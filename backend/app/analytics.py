from datetime import datetime, timezone, date
from collections import defaultdict


def dt(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00"))


def bill_metrics(rows):
    result = []
    previous = {}
    for b in sorted(rows, key=lambda x: x["period_end"]):
        days = (
            date.fromisoformat(b["period_end"]) - date.fromisoformat(b["period_start"])
        ).days
        r = {
            **b,
            "days": days,
            "daily_kwh": b["kwh"] / days,
            "effective_inr_kwh": b["total_inr"] / b["kwh"],
            "change_pct": None,
            "daily_change_pct": None,
        }
        key = (b["account"], b["meter_id"], b["source"] == "demo")
        p = previous.get(key)
        if p and p["period_end"] == b["period_start"]:
            r["change_pct"] = (r["kwh"] / p["kwh"] - 1) * 100
            r["daily_change_pct"] = (r["daily_kwh"] / p["daily_kwh"] - 1) * 100
        previous[key] = r
        result.append(r)
    return result


def intervals(readings):
    result = []
    issues = []
    groups = defaultdict(list)
    for r in readings:
        groups[(r["meter_id"], r["category"], r["unit"], r["source"] == "demo")].append(
            r
        )
    for group in groups.values():
        prior = None
        for r in sorted(group, key=lambda x: dt(x["end"])):
            flags = list(r.get("quality_flags", []))
            start = r.get("start")
            value = r["value"]
            if r["kind"] == "cumulative":
                if prior is None:
                    issues.append({"id": r["id"], "flag": "missing_previous_reading"})
                    prior = r
                    continue
                value -= prior["value"]
                start = prior["end"]
                flags += prior.get("quality_flags", [])
                if value < 0:
                    issues.append(
                        {"id": r["id"], "flag": "counter_reset_or_inconsistent"}
                    )
                    prior = r
                    continue
                prior = r
            if flags:
                issues.append(
                    {"id": r["id"], "flag": "quality_flagged", "details": flags}
                )
                continue
            factor = 1000 if r["unit"] == "m3" else 1
            result.append(
                {
                    **r,
                    "start": start,
                    "end": r["end"],
                    "value": value * factor,
                    "unit": "L" if r["unit"] == "m3" else r["unit"],
                }
            )
    return result, issues


def water_analysis(readings, settings):
    normalized, issues = intervals(readings)
    groups = defaultdict(list)
    for r in normalized:
        if r["category"].startswith("ro_"):
            groups[(dt(r["start"]), dt(r["end"]), r["source"] == "demo")].append(r)
    balances = []
    for (start, end, demo), rows in groups.items():
        cats = {
            c: [r for r in rows if r["category"] == c]
            for c in ["ro_input", "ro_product", "ro_reject"]
        }
        if any(len(v) != 1 for v in cats.values()):
            issues.append(
                {
                    "flag": "missing_or_ambiguous_aligned_RO_channels",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
            )
            continue
        a, b, c = [cats[k][0]["value"] for k in cats]
        if a <= 0:
            issues.append({"flag": "zero_input", "end": end.isoformat()})
            continue
        balances.append(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "input": a,
                "product": b,
                "reject": c,
                "difference": a - b - c,
                "recovery_pct": b / a * 100,
                "rejection_pct": c / a * 100,
                "unit": "L",
                "demo": demo,
                "ids": [r["id"] for r in rows],
                "flag": abs(a - b - c) / a * 100 > settings["water_balance_pct"]
                or b > a
                or c > a,
            }
        )
    now = datetime.now(timezone.utc)
    for r in readings:
        if (now - dt(r["end"])).days > settings["stale_days"]:
            issues.append({"id": r["id"], "flag": "stale"})
    present = {r["category"] for r in normalized if r["source"] != "demo"}
    for category in [
        "ro_input",
        "ro_product",
        "ro_reject",
        "block_1",
        "block_2",
        "block_3",
    ]:
        if category not in present:
            issues.append({"id": category, "flag": "missing_validated_channel"})
    return {
        "balances": sorted(balances, key=lambda b: b["end"]),
        "intervals": normalized,
        "issues": issues,
    }


def alerts_for(bills, water, settings):
    alerts = []
    for b in bill_metrics(
        [b for b in bills if not b.get("quality_flags") and b["source"] != "demo"]
    ):
        if (
            b["daily_change_pct"] is not None
            and b["daily_change_pct"] > settings["increase_pct"]
        ):
            alerts.append(
                {
                    "id": "bill-" + b["id"],
                    "title": "Electricity use increased per day",
                    "severity": "medium",
                    "meter_id": b["meter_id"],
                    "observed": b["daily_kwh"],
                    "unit": "kWh/day",
                    "timestamp": b["period_end"],
                    "baseline": b["daily_kwh"] / (1 + b["daily_change_pct"] / 100),
                    "difference_pct": b["daily_change_pct"],
                    "comparison_window": "Immediately preceding contiguous bill period, normalized by days",
                    "source": b["source"],
                    "source_ref": b["source_ref"],
                    "quality": "Bill transcribed; only two periods compared",
                    "confidence": "Low causal confidence",
                    "causes": [
                        "Longer operating hours or higher occupancy",
                        "Cooling load or equipment changes",
                    ],
                    "checks": [
                        "Review calendar, weather and occupancy",
                        "Check interval submeters before attributing usage",
                    ],
                    "verification_status": "unverified",
                }
            )
    for b in water["balances"]:
        if b["flag"] and not b["demo"]:
            alerts.append(
                {
                    "id": "water-" + b["ids"][0],
                    "title": "RO water balance needs review",
                    "severity": "medium",
                    "meter_id": " / ".join(b["ids"]),
                    "observed": b["difference"],
                    "unit": "L balance difference",
                    "timestamp": b["end"],
                    "baseline": 0,
                    "difference_pct": b["difference"] / b["input"] * 100,
                    "comparison_window": b["start"] + " → " + b["end"],
                    "source": "derived",
                    "source_ref": ", ".join(b["ids"]),
                    "quality": "Aligned input/product/reject records",
                    "confidence": "Low causal confidence",
                    "causes": [
                        "Tank storage changes",
                        "Unmetered branches or measurement error",
                    ],
                    "checks": [
                        "Validate meter calibration and pipe layout",
                        "Inspect for leakage only after checking timing/storage",
                    ],
                    "verification_status": "unverified",
                }
            )
    return alerts


def verify(payload, records, ticket):
    ids = payload["baseline_ids"] + payload["post_ids"]
    if len(set(ids)) != len(ids):
        raise ValueError("Evidence cannot repeat or appear in both windows")
    if any(i not in records for i in ids):
        raise ValueError("Evidence not found")
    rows = [records[i] for i in ids]
    if payload["evidence_type"] == "bills":
        unit = "kWh"
        key = "kwh"
        start_key = "period_start"
        end_key = "period_end"

        def parse(s):
            return datetime.combine(
                date.fromisoformat(s), datetime.min.time(), timezone.utc
            )

        signatures = {(r["account"], r["meter_id"]) for r in rows}
    else:
        if any(r["kind"] != "interval" for r in rows):
            raise ValueError(
                "Verification requires interval evidence; normalize cumulative readings first"
            )
        unit = rows[0]["unit"]
        key = "value"
        start_key = "start"
        end_key = "end"
        parse = dt
        signatures = {(r["meter_id"], r["category"], r["unit"]) for r in rows}
    if len(signatures) != 1:
        raise ValueError("Evidence must use the same meter, resource and unit")
    windows = []
    totals = []
    for group_ids in [payload["baseline_ids"], payload["post_ids"]]:
        group = sorted(
            [records[i] for i in group_ids], key=lambda r: parse(r[start_key])
        )
        for left, right in zip(group, group[1:]):
            if parse(left[end_key]) != parse(right[start_key]):
                raise ValueError(
                    "Each evidence window must be contiguous without overlaps"
                )
        windows.append((parse(group[0][start_key]), parse(group[-1][end_key])))
        totals.append(sum(r[key] for r in group))
    if windows[0][1] > windows[1][0]:
        raise ValueError("Baseline must precede post-action window")
    durations = [(e - s).total_seconds() for s, e in windows]
    reduction = totals[0] * durations[1] / durations[0] - totals[1]
    eligible = (
        ticket["status"] == "closed"
        and payload["comparability_confirmed"]
        and all(r["source"] != "demo" and not r.get("quality_flags") for r in rows)
        and ticket.get("post_start")
        and windows[1][0] >= dt(ticket["post_start"])
        and windows[1][1] <= dt(ticket["post_end"])
    )
    status = payload["requested_status"]
    if any(r.get("quality_flags") for r in rows):
        status = "inconclusive"
    if status == "verified" and not eligible:
        status = "inconclusive"
    if payload["cost_rate"] is not None and not payload["cost_basis"]:
        raise ValueError("Financial estimate requires a cost basis")
    return {
        **payload,
        "status": status,
        "unit": unit,
        "reduction": reduction,
        "baseline_total": totals[0],
        "post_total": totals[1],
        "baseline_seconds": durations[0],
        "post_seconds": durations[1],
        "financial_estimate": reduction * payload["cost_rate"]
        if payload["cost_rate"] is not None
        else None,
        "financial_status": "estimated"
        if payload["cost_rate"] is not None
        else "unavailable",
        "method": "Baseline rate × post-window duration − post consumption",
        "reason": "Operator-reviewed comparability with closed-ticket evidence"
        if status == "verified"
        else "Estimate or insufficient validated comparable evidence; not verified savings",
        "evidence_snapshot": rows,
    }


def score(bills, readings, verifications, settings):
    good = [r for r in readings if not r.get("quality_flags") and r["source"] != "demo"]
    categories = {r["category"] for r in good}
    complete = (
        (
            int(bool(bills))
            + sum(
                c in categories
                for c in [
                    "ro_input",
                    "ro_product",
                    "ro_reject",
                    "block_1",
                    "block_2",
                    "block_3",
                ]
            )
        )
        / 7
        * 100
    )
    metrics = bill_metrics(
        [b for b in bills if not b.get("quality_flags") and b["source"] != "demo"]
    )
    change = metrics[-1]["daily_change_pct"] if metrics else None
    components = {
        "completeness": complete,
        "trend": None if change is None else max(0, min(100, 50 - change)),
        "verified_actions": 100
        if any(v["status"] == "verified" and v["reduction"] > 0 for v in verifications)
        else 0,
    }
    available = sum(
        settings["score_weights"][k] for k, v in components.items() if v is not None
    )
    value = (
        sum(
            v * settings["score_weights"][k]
            for k, v in components.items()
            if v is not None
        )
        / available
        if available
        else None
    )
    return {
        "value": value,
        "components": components,
        "weights": settings["score_weights"],
        "coverage_weight": available,
        "method": "Completeness: 7 resource channels. Trend: clamp(50 − latest daily electricity change %, 0,100). Verified actions: 100 if any positive verified outcome, otherwise 0. Missing components excluded and available weights renormalized. Not an official certification.",
    }
