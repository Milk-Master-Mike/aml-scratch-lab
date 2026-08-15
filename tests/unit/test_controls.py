from pathlib import Path

from engine.aml.controls import load_control
from engine.aml.evaluator import evaluate_rapid_movement
from engine.scenarios.generator import generate_scenario
from engine.scenarios.loader import load_scenario

ROOT = Path(__file__).resolve().parents[2]
CONTROL = load_control(ROOT / "controls/AML-RMF-001.yaml")


def scenario(name: str):
    return load_scenario(ROOT / f"scenarios/{name}/scenario.yaml")


def test_normal_activity_does_not_alert():
    dataset = generate_scenario(scenario("normal"), 194028)
    assert evaluate_rapid_movement(CONTROL, dataset.transactions) is None


def test_rapid_movement_alerts_once_with_high_severity():
    dataset = generate_scenario(scenario("rapid-movement"), 194028)
    alert = evaluate_rapid_movement(CONTROL, dataset.transactions)
    assert alert is not None
    assert alert.severity == "high"
    assert len(alert.transaction_ids) == 4


def test_monitoring_view_hides_scenario_answer_key():
    dataset = generate_scenario(scenario("rapid-movement"), 194028)
    injected = next(tx for tx in dataset.transactions if tx.scenario_id)
    assert "scenario_id" not in injected.monitoring_view()
