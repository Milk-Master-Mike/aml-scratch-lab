from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from engine.models import ScenarioDataset, Transaction
from engine.scenarios.loader import ScenarioDefinition
from engine.synthetic.generator import SIMULATION_END, generate_bank, stable_id


def generate_scenario(definition: ScenarioDefinition, seed: int, days: int = 30) -> ScenarioDataset:
    customers, accounts, baseline = generate_bank(seed, days=days)
    txs = list(baseline)
    tagged: list[Transaction] = []
    alerting = definition.case == "should-alert"
    hub = accounts[0]

    def tx(
        index: int,
        source: str | None,
        destination: str | None,
        amount: str,
        hours: float,
        kind: str = "ACH",
    ) -> Transaction:
        return Transaction(
            stable_id(seed, f"{definition.key}-tx", index),
            source,
            destination,
            Decimal(amount),
            "USD",
            kind,
            SIMULATION_END + timedelta(hours=hours),
            "US",
            definition.id,
        )

    family = definition.family
    if family == "rapid-movement" and alerting:
        tagged = [tx(0, None, hub.account_id, "15000", 0, "WIRE")]
        tagged += [
            tx(i, hub.account_id, accounts[i].account_id, "4200", i * 2) for i in range(1, 4)
        ]
    elif family == "abnormal-velocity":
        count = 12 if alerting else 5
        tagged = [
            tx(i, hub.account_id, accounts[(i % 7) + 1].account_id, "95", i / 20)
            for i in range(count)
        ]
    elif family in {"volume-deviation", "legitimate-high-volume"}:
        if family == "legitimate-high-volume" and not alerting:
            customers = (
                replace(customers[0], expected_monthly_volume=Decimal(100000)),
                *customers[1:],
            )
            amount = "60000"
        else:
            amount = "50000" if alerting else "12000"
        tagged = [tx(0, None, hub.account_id, amount, 0, "WIRE")]
    elif family == "funnel-activity":
        source_count = 4 if alerting else 2
        tagged = [
            tx(i, accounts[i + 1].account_id, hub.account_id, "3000", i)
            for i in range(source_count)
        ]
        outgoing_amount = "10800" if alerting else "2000"
        tagged.append(tx(10, hub.account_id, accounts[6].account_id, outgoing_amount, 6, "WIRE"))
    elif family == "circular-flow":
        tagged = [
            tx(0, accounts[0].account_id, accounts[1].account_id, "5000", 0),
            tx(1, accounts[1].account_id, accounts[2].account_id, "4900", 2),
        ]
        destination = accounts[0].account_id if alerting else accounts[3].account_id
        tagged.append(tx(2, accounts[2].account_id, destination, "4800", 4))
    elif family == "dormant-activation":
        account_id = hub.account_id
        txs = [
            item
            for item in txs
            if account_id not in (item.source_account, item.destination_account)
        ]
        old = Transaction(
            stable_id(seed, f"{definition.key}-old", 0),
            None,
            account_id,
            Decimal(25),
            "USD",
            "ACH",
            SIMULATION_END - timedelta(days=400),
            "US",
            definition.id,
        )
        amount = "12000" if alerting else "500"
        tagged = [old, tx(1, None, account_id, amount, 0, "WIRE")]
    elif family == "customer-profile-mismatch":
        customers = (replace(customers[0], expected_monthly_volume=Decimal(5000)), *customers[1:])
        tagged = [tx(0, None, hub.account_id, "20000" if alerting else "6000", 0, "WIRE")]

    return ScenarioDataset(
        definition.key,
        definition.id,
        seed,
        customers,
        accounts,
        tuple(txs + tagged),
        definition.expected.alert,
        definition.expected.severity,
    )
