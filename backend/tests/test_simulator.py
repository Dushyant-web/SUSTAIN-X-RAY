from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.simulator import Simulator, SimulationConfig
from app.main import create_app
from app.store import Store
from app.auth import identity

BASE = datetime(2026, 10, 27, tzinfo=timezone.utc)


def frame(scenario="normal"):
    s = Simulator()
    s.start(SimulationConfig(scenario=scenario), BASE)
    return s, s.tick(BASE + timedelta(seconds=3))


def test_units_and_demo_provenance():
    s, f = frame()
    assert len(f["readings"]) == 7
    assert all(
        r["source"] == "demo" and r["meter_id"].startswith("DEMO-")
        for r in f["readings"]
    )
    assert f["energy_kwh"] == pytest.approx(f["electricity_kw"] * 3 / 3600, abs=1e-6)
    assert f["balance_l"] == pytest.approx(0, abs=1e-9)
    assert f["recovery_pct"] == 65
    assert not f["alerts"]
    assert s.tick(BASE + timedelta(seconds=4)) is None


def test_scenarios():
    _, spike = frame("electricity_spike")
    assert spike["electricity_kw"] > 120 * 1.2 and len(spike["alerts"]) == 1
    _, gap = frame("ro_imbalance")
    assert gap["balance_l"] > 0 and gap["alerts"]
    _, missing = frame("sensor_dropout")
    assert missing["balance_l"] is None and missing["rejection_pct"] is None
    assert len(missing["readings"]) == 6 and missing["reject_lpm"] is None


def test_pause_resume_and_buffer():
    s, f = frame()
    s.pause()
    assert s.tick(BASE + timedelta(seconds=20)) is None
    s.start(SimulationConfig(), BASE + timedelta(seconds=30))
    assert s.tick(BASE + timedelta(seconds=33))["seconds"] == 3
    with pytest.raises(ValueError):
        s.reset()
    for i in range(1, 250):
        s.tick(BASE + timedelta(seconds=33 + i * 3))
    assert len(s.snapshot()["frames"]) == 240
    s.pause()
    s.reset()
    assert s.snapshot()["frames"] == []


def test_validation_and_seed():
    with pytest.raises(ValueError):
        SimulationConfig(interval_seconds=0)
    with pytest.raises(ValueError):
        SimulationConfig(baseline_kw=float("nan"))
    with pytest.raises(ValueError):
        SimulationConfig(scenario="real")
    _, a = frame()
    _, b = frame()
    assert a["electricity_kw"] == b["electricity_kw"]


def test_api_isolation_and_roles(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "production")
    store = Store(str(tmp_path / "test.sqlite"))
    app = create_app(store)
    store.put("users", "operator", {"role": "operator", "active": True})
    app.dependency_overrides[identity] = lambda: {"uid": "operator"}
    with TestClient(app) as client:
        assert client.post("/api/simulator/start", json={}).status_code == 200
        assert client.post("/api/simulator/start", json={}).status_code == 409
        sim = app.state.simulator
        sim.tick(sim.previous + timedelta(seconds=3))
        assert client.get("/api/simulator").json()["total_frames"] == 1
        assert client.get("/api/dashboard").json()["readings"] == []
        assert store.all("readings") == []
        client.post("/api/simulator/pause")
        assert client.post("/api/simulator/reset").status_code == 200
        store.put("users", "operator", {"role": "viewer", "active": True})
        assert client.get("/api/simulator").status_code == 200
        assert client.post("/api/simulator/start", json={}).status_code == 403
