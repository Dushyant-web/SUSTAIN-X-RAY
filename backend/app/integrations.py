"""No enabled hardware adapter. Register only after commissioning the real interface."""

from typing import Protocol, Iterable
from .models import Reading


class MeterAdapter(Protocol):
    def health(self) -> dict: ...
    def fetch(self, since: str) -> Iterable[Reading]: ...


class UnconfiguredAdapter:
    def health(self):
        return {
            "status": "unconfigured",
            "live": False,
            "reason": "Meter model, protocol and calibration are not verified",
        }

    def fetch(self, since):
        raise RuntimeError("No commissioned hardware source")
