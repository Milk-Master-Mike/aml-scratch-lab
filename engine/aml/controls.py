from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Conditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum_incoming: float | None = Field(default=None, gt=0)
    outgoing_ratio: float | None = Field(default=None, gt=0)
    minimum_counterparties: int | None = Field(default=None, ge=1)
    window_hours: int | None = Field(default=None, gt=0)
    minimum_transactions: int | None = Field(default=None, ge=1)
    maximum_transactions: int | None = Field(default=None, ge=1)
    volume_multiplier: float | None = Field(default=None, gt=0)
    minimum_sources: int | None = Field(default=None, ge=1)
    minimum_hops: int | None = Field(default=None, ge=2)
    dormant_days: int | None = Field(default=None, ge=1)
    activation_amount: float | None = Field(default=None, gt=0)
    minimum_amount: float | None = Field(default=None, gt=0)


REQUIRED_CONDITIONS = {
    "rapid_movement": {
        "minimum_incoming",
        "outgoing_ratio",
        "minimum_counterparties",
        "window_hours",
    },
    "abnormal_velocity": {"minimum_transactions", "window_hours"},
    "volume_deviation": {"volume_multiplier"},
    "funnel_activity": {"minimum_incoming", "outgoing_ratio", "minimum_sources", "window_hours"},
    "circular_flow": {"minimum_hops", "window_hours", "minimum_amount"},
    "dormant_activation": {"dormant_days", "activation_amount"},
    "profile_mismatch": {"volume_multiplier"},
}


class ControlDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    version: int = Field(ge=1)
    enabled: bool
    owner: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    evaluator: Literal[
        "rapid_movement",
        "abnormal_velocity",
        "volume_deviation",
        "funnel_activity",
        "circular_flow",
        "dormant_activation",
        "profile_mismatch",
    ]
    scenario_coverage: list[str] = Field(min_length=1)
    conditions: Conditions
    evidence: list[str]

    @model_validator(mode="after")
    def validate_conditions(self) -> ControlDefinition:
        missing = [
            name
            for name in REQUIRED_CONDITIONS[self.evaluator]
            if getattr(self.conditions, name) is None
        ]
        if missing:
            raise ValueError(f"{self.evaluator} requires conditions: {', '.join(sorted(missing))}")
        return self

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def load_control(path: Path) -> ControlDefinition:
    return ControlDefinition.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_controls(root: Path) -> dict[str, ControlDefinition]:
    controls: dict[str, ControlDefinition] = {}
    for path in sorted(root.glob("*.yaml")):
        control = load_control(path)
        if control.id in controls:
            raise ValueError(f"Duplicate control id: {control.id}")
        controls[control.id] = control
    return controls
