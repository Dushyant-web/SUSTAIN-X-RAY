"""Bounded, process-local demo stream. Never writes production measurement collections."""

import asyncio
import math
import random
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Literal
from pydantic import Field
from .models import Model, Reading


class SimulationConfig(Model):
    scenario: Literal[
        "normal", "electricity_spike", "ro_imbalance", "sensor_dropout"
    ] = "normal"
    interval_seconds: int = Field(default=3, ge=1, le=30)
    baseline_kw: float = Field(default=120, gt=0, le=100000)
    input_lpm: float = Field(default=60, gt=0, le=100000)
    seed: int = Field(default=42, ge=0, le=2147483647)


class Simulator:
    def __init__(self):
        self.lock = threading.RLock()
        self.config = SimulationConfig()
        self.running = False
        self.run_id = uuid.uuid4().hex[:10]
        self.frames = deque(maxlen=240)
        self.rng = random.Random(self.config.seed)
        self.previous = None
        self.started_at = None
        self.updated_at = None
        self.total_frames = 0
        self.error = None

    def start(self, config, at=None):
        with self.lock:
            if self.running:
                raise ValueError(
                    "Simulator already running; pause before changing configuration"
                )
            self.config = config
            self.rng = random.Random(config.seed + self.total_frames)
            self.previous = at or datetime.now(timezone.utc)
            self.started_at = self.previous.isoformat()
            self.running = True
            self.error = None

    def pause(self):
        with self.lock:
            self.running = False

    def reset(self):
        with self.lock:
            if self.running:
                raise ValueError("Pause before clearing the synthetic buffer")
            self.frames.clear()
            self.total_frames = 0
            self.run_id = uuid.uuid4().hex[:10]
            self.updated_at = None
            self.started_at = None
            self.previous = None
            self.error = None

    def tick(self, at=None):
        with self.lock:
            if not self.running:
                return None
            end = at or datetime.now(timezone.utc)
            seconds = (end - self.previous).total_seconds()
            if seconds < self.config.interval_seconds:
                return None
            c = self.config
            noise = self.rng.uniform(-0.025, 0.025)
            kw = c.baseline_kw * (1 + 0.04 * math.sin(self.total_frames / 8) + noise)
            if c.scenario == "electricity_spike":
                kw *= 1.8
            feed = c.input_lpm * (1 + noise)
            product = feed * (0.5 if c.scenario == "ro_imbalance" else 0.65)
            reject = feed * 0.35
            rates = {
                "electricity": kw,
                "ro_input": feed,
                "ro_product": product,
                "ro_reject": reject,
                "block_1": 11 * (1 + noise),
                "block_2": 14 * (1 + noise),
                "block_3": 9 * (1 + noise),
            }
            rows = []
            for category, rate in rates.items():
                if c.scenario == "sensor_dropout" and category == "ro_reject":
                    continue
                electricity = category == "electricity"
                row = Reading(
                    meter_id=f"DEMO-{self.run_id}-{category}",
                    category=category,
                    unit="kWh" if electricity else "L",
                    kind="interval",
                    value=rate * seconds / (3600 if electricity else 60),
                    start=self.previous,
                    end=end,
                    source="demo",
                    source_ref=f"Synthetic simulator {self.run_id}; scenario={c.scenario}; seed={c.seed}",
                )
                rows.append(
                    {
                        **row.model_dump(mode="json"),
                        "id": f"{self.run_id}-{self.total_frames}-{category}",
                    }
                )
            alerts = []
            if kw > c.baseline_kw * 1.2:
                alerts.append(
                    {
                        "title": "Simulated electricity spike",
                        "severity": "medium",
                        "observed": round(kw, 2),
                        "baseline": c.baseline_kw,
                        "unit": "kW",
                        "difference_pct": round((kw / c.baseline_kw - 1) * 100, 2),
                        "check": "Inspect operating schedule or unexpected equipment load.",
                        "cause": "Scenario injects extra load; not a campus diagnosis.",
                    }
                )
            difference = feed - product - reject
            dropout = c.scenario == "sensor_dropout"
            if dropout:
                alerts.append(
                    {
                        "title": "Simulated missing reject sensor",
                        "severity": "medium",
                        "check": "Check sensor connectivity and timestamps before calculating RO balance.",
                        "cause": "Dropout deliberately injected by the simulator.",
                    }
                )
            elif abs(difference) / feed > 0.1:
                alerts.append(
                    {
                        "title": "Simulated RO balance mismatch",
                        "severity": "medium",
                        "observed": round(difference, 2),
                        "baseline": 0,
                        "unit": "L/min",
                        "check": "Check storage changes, calibration and unmetered branches; do not assume a leak.",
                        "cause": "Scenario deliberately reduces measured product flow.",
                    }
                )
            frame = {
                "timestamp": end.isoformat(),
                "seconds": seconds,
                "scenario": c.scenario,
                "electricity_kw": round(kw, 3),
                "energy_kwh": kw * seconds / 3600,
                "input_lpm": feed,
                "product_lpm": product,
                "reject_lpm": None if dropout else reject,
                "balance_l": None if dropout else difference * seconds / 60,
                "recovery_pct": None if dropout else product / feed * 100,
                "rejection_pct": None if dropout else reject / feed * 100,
                "block_1_lpm": rates["block_1"],
                "block_2_lpm": rates["block_2"],
                "block_3_lpm": rates["block_3"],
                "readings": rows,
                "alerts": alerts,
                "source": "demo",
            }
            self.frames.append(frame)
            self.previous = end
            self.updated_at = end.isoformat()
            self.total_frames += 1
            return frame

    def snapshot(self):
        with self.lock:
            age = (
                (
                    datetime.now(timezone.utc) - datetime.fromisoformat(self.updated_at)
                ).total_seconds()
                if self.updated_at
                else None
            )
            return {
                "running": self.running,
                "run_id": self.run_id,
                "config": self.config.model_dump(),
                "started_at": self.started_at,
                "updated_at": self.updated_at,
                "age_seconds": age,
                "stale": age is not None and age > self.config.interval_seconds * 3,
                "total_frames": self.total_frames,
                "retained_frames": len(self.frames),
                "capacity": 240,
                "frames": list(self.frames),
                "error": self.error,
                "source": "demo",
                "storage": "process-memory; cleared on server restart; separate from campus records",
            }

    async def run(self):
        while True:
            await asyncio.sleep(0.25)
            try:
                self.tick()
            except Exception:
                with self.lock:
                    self.error = "Generation failed; simulator paused. Review server configuration."
                    self.running = False
