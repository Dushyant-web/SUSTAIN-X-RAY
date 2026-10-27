import json
import pytest
from fastapi.testclient import TestClient
from app.models import Bill, Reading, Settings
from app.analytics import bill_metrics, intervals, water_analysis, verify, alerts_for
from app.main import create_app, ROOT
from app.store import Store
from app.auth import identity


@pytest.fixture
def bills():
    return [
        {**r, "id": str(i)}
        for i, r in enumerate(json.loads((ROOT / "data/bills.json").read_text()))
    ]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "local")
    return TestClient(create_app(Store(str(tmp_path / "test.sqlite"))))


def reading(
    category="ro_input",
    value=100,
    start="2026-08-01T00:00:00+00:00",
    end="2026-08-02T00:00:00+00:00",
    **kw,
):
    return {
        "id": category + end,
        "meter_id": category,
        "category": category,
        "unit": "L",
        "kind": "interval",
        "value": value,
        "start": start,
        "end": end,
        "source": "manual",
        "source_ref": "test evidence",
        "quality_flags": [],
        **kw,
    }


def test_bill_calculations(bills):
    r = bill_metrics(bills)
    assert r[2]["kwh"] == 3101811.4
    assert r[2]["kvah"] == 3135321.59
    assert r[2]["effective_inr_kwh"] == pytest.approx(30545123 / 3101811.4)
    assert r[1]["days"] == 31
    assert r[1]["change_pct"] == pytest.approx(26.61173223865)
    assert r[1]["daily_change_pct"] == pytest.approx(
        (3008147.23 / 31 / (2375883.48 / 30) - 1) * 100
    )
    assert r[2]["change_pct"] == pytest.approx(3.113683, rel=1e-5)


def test_no_baseline_across_gap_or_meter(bills):
    assert bill_metrics([bills[0], bills[2]])[1]["change_pct"] is None
    bills[1]["meter_id"] = "other"
    assert bill_metrics(bills[:2])[1]["change_pct"] is None


def test_bill_validation(bills):
    b = {k: v for k, v in bills[0].items() if k != "id"}
    for changes in [
        {"kwh": 0},
        {"kwh": float("nan")},
        {"period_end": b["period_start"]},
        {"extra": "bad"},
    ]:
        with pytest.raises(ValueError):
            Bill(**{**b, **changes})


def test_water_balance():
    rows = [reading(), reading("ro_product", 60), reading("ro_reject", 35)]
    b = water_analysis(rows, Settings().model_dump())["balances"][0]
    assert b["difference"] == 5 and b["recovery_pct"] == 60 and b["rejection_pct"] == 35
    rows[2]["unit"] = "m3"
    rows[2]["value"] = 0.035
    assert (
        water_analysis(rows, Settings().model_dump())["balances"][0]["difference"] == 5
    )


@pytest.mark.parametrize(
    "change",
    [{"end": "2026-08-03T00:00:00+00:00"}, {"quality_flags": ["uncertain_unit"]}],
)
def test_misaligned_missing_water(change):
    rows = [
        reading(),
        reading("ro_product", 60),
        {**reading("ro_reject", 40), **change},
    ]
    result = water_analysis(rows, Settings().model_dump())
    assert not result["balances"] and result["issues"]


def test_zero_input_and_counter_reset():
    result = water_analysis(
        [reading(value=0), reading("ro_product", 0), reading("ro_reject", 0)],
        Settings().model_dump(),
    )
    assert result["issues"][0]["flag"] == "zero_input"
    a = reading(kind="cumulative", start=None, value=100)
    b = reading(
        kind="cumulative", start=None, value=150, end="2026-08-03T00:00:00+00:00"
    )
    rows, issues = intervals([a, b])
    assert rows[0]["value"] == 50 and issues[0]["flag"] == "missing_previous_reading"
    b["value"] = 50
    rows, issues = intervals([a, b])
    assert not rows and issues[-1]["flag"] == "counter_reset_or_inconsistent"


def test_timezone_and_unit_validation():
    for changes in [
        {"end": "2026-08-02T00:00:00"},
        {"unit": "kWh"},
        {"start": None},
        {"value": -1},
    ]:
        with pytest.raises(ValueError):
            Reading(**{k: v for k, v in reading(**changes).items() if k != "id"})


def test_thresholds(bills):
    empty = {"balances": []}
    assert len(alerts_for(bills, empty, Settings(increase_pct=20).model_dump())) == 1
    assert not alerts_for(bills, empty, Settings(increase_pct=30).model_dump())
    with pytest.raises(ValueError):
        Settings(increase_pct=-1)
    with pytest.raises(ValueError):
        Settings(score_weights={"completeness": 30})


def test_csv_atomic_duplicates(client):
    csv = "account,invoice,meter_id,period_start,period_end,kwh,total_inr,source_ref\na,one,m,2026-01-01,2026-02-01,100,900,test\n"
    assert (
        client.post(
            "/api/import/bills", content=csv, headers={"Content-Type": "text/plain"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/import/bills", content=csv, headers={"Content-Type": "text/plain"}
        ).status_code
        == 409
    )
    bad = (
        csv.replace("one", "two")
        .replace("2026-01-01", "2026-03-01")
        .replace("2026-02-01", "2026-04-01")
        + "a,three,m,2026-04-01,2026-05-01,-1,900,test\n"
    )
    assert (
        client.post(
            "/api/import/bills", content=bad, headers={"Content-Type": "text/plain"}
        ).status_code
        == 422
    )
    assert len(client.get("/api/dashboard").json()["bills"]) == 1
    assert (
        client.post(
            "/api/import/bills",
            content=csv.splitlines()[0],
            headers={"Content-Type": "text/plain"},
        ).status_code
        == 422
    )


def test_timestamp_duplicate(client):
    r = {k: v for k, v in reading().items() if k != "id"}
    assert client.post("/api/readings", json=r).status_code == 201
    r["end"] = "2026-08-02T05:30:00+05:30"
    assert client.post("/api/readings", json=r).status_code == 409


def test_verification_status():
    a = reading(value=100)
    b = reading(
        value=80, start="2026-08-02T00:00:00+00:00", end="2026-08-03T00:00:00+00:00"
    )
    p = {
        "ticket_id": "t",
        "baseline_ids": [a["id"]],
        "post_ids": [b["id"]],
        "evidence_type": "readings",
        "requested_status": "verified",
        "context": "Same operating hours and occupancy",
        "comparability_confirmed": True,
        "cost_rate": None,
        "cost_basis": "",
    }
    t = {"status": "closed", "post_start": b["start"], "post_end": b["end"]}
    result = verify(p, {a["id"]: a, b["id"]: b}, t)
    assert (
        result["status"] == "verified"
        and result["reduction"] == 20
        and result["financial_estimate"] is None
    )
    b["source"] = "demo"
    assert verify(p, {a["id"]: a, b["id"]: b}, t)["status"] == "inconclusive"
    b["source"] = "manual"
    p["requested_status"] = "estimated"
    p["cost_rate"] = 2
    p["cost_basis"] = "Supported test cost"
    assert verify(p, {a["id"]: a, b["id"]: b}, t)["financial_estimate"] == 40
    p["post_ids"] = p["baseline_ids"]
    with pytest.raises(ValueError):
        verify(p, {a["id"]: a, b["id"]: b}, t)


def test_ticket_closure_audit(client):
    t = {"title": "Inspect RO", "owner": "Operator", "status": "open"}
    r = client.post("/api/tickets", json=t)
    assert r.status_code == 201
    id = r.json()["id"]
    t["status"] = "closed"
    assert client.put("/api/tickets/" + id, json=t).status_code == 422
    t.update(
        findings="Valve inspected",
        corrective_action="Adjusted valve",
        post_start="2026-08-01T00:00:00Z",
        post_end="2026-08-02T00:00:00Z",
    )
    r = client.put("/api/tickets/" + id, json=t)
    assert len(r.json()["history"]) == 2


def test_auth_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "production")
    c = TestClient(create_app(Store(str(tmp_path / "auth.sqlite"))))
    assert c.get("/api/dashboard").status_code == 401
    assert c.post("/api/seed").status_code == 401
    assert (
        c.get("/api/dashboard", headers={"Authorization": "Bearer fake"}).status_code
        == 401
    )


def test_role_enforcement(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "production")
    s = Store(str(tmp_path / "auth.sqlite"))
    s.put("users", "v", {"role": "viewer", "active": True})
    app = create_app(s)
    app.dependency_overrides[identity] = lambda: {"uid": "v"}
    c = TestClient(app)
    assert c.get("/api/dashboard").status_code == 200
    assert c.post("/api/seed").status_code == 403
    assert (
        c.post("/api/tickets", json={"title": "Ticket", "owner": "a"}).status_code
        == 403
    )
    assert c.get("/api/registry/users").status_code == 403
    s.put("users", "v", {"role": "operator", "active": False})
    assert c.get("/api/dashboard").status_code == 403


def test_reports_and_export(client):
    client.post("/api/seed")
    r = client.get("/api/reports?start=2026-07-01&end=2026-07-31")
    assert len(r.json()["bills"]) == 1
    assert client.get("/api/reports?start=2026-08-01&end=2026-07-01").status_code == 422
    r = client.get("/api/export/bills?start=2026-06-01&end=2026-08-31")
    assert r.status_code == 200 and "kwh" in r.text


def test_demo_not_in_alerts(bills):
    for b in bills:
        b["source"] = "demo"
    assert not alerts_for(bills, {"balances": []}, Settings().model_dump())


def test_empty_water_flags_missing_channels():
    result = water_analysis([], Settings().model_dump())
    assert len(result["issues"]) == 6
    assert all(i["flag"] == "missing_validated_channel" for i in result["issues"])
