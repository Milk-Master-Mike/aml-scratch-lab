from pathlib import Path

import pytest

from engine.aml.controls import load_controls
from engine.aml.evaluator import evaluate
from engine.scenarios.generator import generate_scenario
from engine.scenarios.loader import load_scenarios

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("seed", [9, 194028])
def test_every_scenario_matches_its_expected_result(seed: int):
    scenarios = load_scenarios(ROOT / "scenarios")
    controls = load_controls(ROOT / "controls")
    assert len(scenarios) == 16
    for scenario in scenarios.values():
        alert = evaluate(controls[scenario.control_id], generate_scenario(scenario, seed))
        assert (alert is not None) == scenario.expected.alert, scenario.key
        if alert:
            assert alert.severity == scenario.expected.severity, scenario.key


def test_each_m2_family_has_alert_and_no_alert_coverage():
    scenarios = load_scenarios(ROOT / "scenarios")
    families: dict[str, set[str]] = {}
    for scenario in scenarios.values():
        families.setdefault(scenario.family, set()).add(scenario.case)
    assert all(cases == {"should-alert", "should-not-alert"} for cases in families.values())


def test_control_metadata_maps_to_existing_scenarios():
    scenarios = load_scenarios(ROOT / "scenarios")
    controls = load_controls(ROOT / "controls")
    assert len(controls) == 7
    for control in controls.values():
        assert control.owner
        assert set(control.scenario_coverage) <= scenarios.keys()
