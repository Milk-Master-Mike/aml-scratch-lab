from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ExpectedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert: bool
    severity: str | None = None


class ScenarioDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    id: str
    version: int = Field(ge=1)
    family: str
    case: Literal["should-alert", "should-not-alert"]
    control_id: str
    name: str
    description: str
    expected: ExpectedResult


def load_scenario(path: Path) -> ScenarioDefinition:
    return ScenarioDefinition.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_scenarios(root: Path) -> dict[str, ScenarioDefinition]:
    scenarios: dict[str, ScenarioDefinition] = {}
    for path in sorted(root.glob("*/scenario.yaml")):
        scenario = load_scenario(path)
        if scenario.key in scenarios:
            raise ValueError(f"Duplicate scenario key: {scenario.key}")
        scenarios[scenario.key] = scenario
    return scenarios
