from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_strip_whitespace=True
    )


class Evidence(Model):
    source: Literal["manual", "imported", "actual", "demo"] = "manual"
    source_ref: str = Field(min_length=1, max_length=500)
    quality_flags: list[str] = Field(default_factory=list, max_length=20)


class Bill(Evidence):
    account: str = Field(min_length=1, max_length=80)
    invoice: str = Field(min_length=1, max_length=80)
    meter_id: str = Field(min_length=1, max_length=80)
    period_start: date
    period_end: date
    kwh: float = Field(gt=0)
    kvah: float | None = Field(default=None, gt=0)
    total_inr: float = Field(ge=0)
    demand_kva: float | None = Field(default=None, ge=0)
    energy_rate: float | None = Field(default=None, ge=0)
    energy_rate_unit: Literal["INR/kWh", "INR/kVAh"] = "INR/kVAh"
    demand_charges_inr: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def dates(self):
        if self.period_end <= self.period_start:
            raise ValueError("Period end must follow start")
        return self


Category = Literal[
    "ro_input",
    "ro_product",
    "ro_reject",
    "block_1",
    "block_2",
    "block_3",
    "electricity",
]


class Reading(Evidence):
    meter_id: str = Field(min_length=1, max_length=80)
    category: Category
    unit: Literal["L", "m3", "kWh"]
    kind: Literal["interval", "cumulative"]
    value: float = Field(ge=0)
    start: datetime | None = None
    end: datetime

    @model_validator(mode="after")
    def valid(self):
        if self.end.tzinfo is None or (self.start and self.start.tzinfo is None):
            raise ValueError("Timezone offset required")
        if self.kind == "interval" and not self.start:
            raise ValueError("Interval start required")
        if self.start and self.start >= self.end:
            raise ValueError("End must follow start")
        if (self.category == "electricity") != (self.unit == "kWh"):
            raise ValueError("Unit incompatible with category")
        return self


class Ticket(Model):
    title: str = Field(min_length=3, max_length=200)
    alert_id: str | None = None
    owner: str = Field(min_length=1, max_length=100)
    priority: Literal["low", "medium", "high"] = "medium"
    status: Literal["open", "in_progress", "closed"] = "open"
    findings: str = Field(default="", max_length=5000)
    corrective_action: str = Field(default="", max_length=5000)
    post_start: datetime | None = None
    post_end: datetime | None = None

    @model_validator(mode="after")
    def closing(self):
        if bool(self.post_start) != bool(self.post_end):
            raise ValueError("Both post-action dates required")
        if self.post_start and (
            self.post_start.tzinfo is None
            or self.post_end.tzinfo is None
            or self.post_end <= self.post_start
        ):
            raise ValueError("Invalid post-action window")
        if self.status == "closed" and (
            not self.findings or not self.corrective_action or not self.post_start
        ):
            raise ValueError(
                "Closure requires findings, corrective action and post-action window"
            )
        return self


class Verification(Model):
    ticket_id: str
    baseline_ids: list[str] = Field(min_length=1, max_length=100)
    post_ids: list[str] = Field(min_length=1, max_length=100)
    evidence_type: Literal["bills", "readings"]
    requested_status: Literal["estimated", "verified", "inconclusive"] = "estimated"
    context: str = Field(min_length=10, max_length=5000)
    comparability_confirmed: bool = False
    cost_rate: float | None = Field(default=None, ge=0)
    cost_basis: str = Field(default="", max_length=1000)


class Settings(Model):
    increase_pct: float = Field(default=20, ge=0, le=1000)
    stale_days: int = Field(default=45, ge=1, le=3650)
    water_balance_pct: float = Field(default=10, ge=0, le=100)
    marginal_kwh_rate: float | None = Field(default=None, ge=0)
    tariff_basis: str = Field(default="", max_length=1000)
    scenario_pcts: list[float] = Field(default=[2, 5, 10], min_length=1, max_length=10)
    score_weights: dict[str, float] = Field(
        default={"completeness": 40, "trend": 30, "verified_actions": 30}
    )

    @model_validator(mode="after")
    def valid(self):
        if any(p <= 0 or p > 100 for p in self.scenario_pcts):
            raise ValueError("Scenarios must be in (0,100]")
        if (
            set(self.score_weights) != {"completeness", "trend", "verified_actions"}
            or any(w < 0 for w in self.score_weights.values())
            or abs(sum(self.score_weights.values()) - 100) > 0.001
        ):
            raise ValueError("Score weights must total 100")
        if self.marginal_kwh_rate is not None and not self.tariff_basis:
            raise ValueError("Tariff basis required")
        return self


class Registry(Model):
    name: str = Field(min_length=1, max_length=100)
    resource: Literal["electricity", "water", "campus"] = "campus"
    location: str = Field(default="", max_length=200)
    source_ref: str = Field(min_length=1, max_length=500)
    connectivity: Literal["unverified", "manual", "csv", "verified_adapter"] = (
        "unverified"
    )
    notes: str = Field(default="", max_length=1000)


class UserRole(Model):
    name: str = Field(min_length=1, max_length=100)
    role: Literal["viewer", "operator", "admin"]
    active: bool = True
