from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from engine.models import Account, Customer, Transaction

NAMESPACE = uuid.UUID("fd8cf4ad-105a-49c4-b610-4235249bbca4")
SIMULATION_END = datetime(2026, 1, 31, 12, tzinfo=timezone.utc)
FIRST = ("Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Morgan", "Riley")
LAST = ("Brooks", "Chen", "Davis", "Garcia", "Johnson", "Patel", "Rivera", "Williams")
BUSINESSES = ("Northstar Supply", "Blue Ridge Works", "Harbor Studio", "Summit Services")


def stable_id(seed: int, kind: str, index: int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{seed}:{kind}:{index}"))


def generate_bank(seed: int, customer_count: int = 8, days: int = 30):
    rng = random.Random(seed)
    customers: list[Customer] = []
    accounts: list[Account] = []
    transactions: list[Transaction] = []
    for index in range(customer_count):
        kind = "company" if index % 4 == 3 else "person"
        name = (
            f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            if kind == "person"
            else f"{rng.choice(BUSINESSES)} LLC"
        )
        customer_id = stable_id(seed, "customer", index)
        expected = Decimal(rng.randrange(40, 180) * 100)
        customers.append(
            Customer(
                customer_id,
                name,
                kind,
                "demo services",
                rng.choice(("low", "medium")),
                "US",
                expected,
                SIMULATION_END - timedelta(days=700 + index),
                seed,
            )
        )
        account_id = stable_id(seed, "account", index)
        accounts.append(
            Account(
                account_id,
                customer_id,
                "checking",
                customers[-1].opened_at,
                "active",
                expected * Decimal("1.5"),
            )
        )

    tx_index = 0
    for day in range(days):
        for destination in accounts:
            if rng.random() < 0.42:
                amount = Decimal(rng.randrange(25, 240)) + Decimal("0.50")
                source = accounts[rng.randrange(len(accounts))]
                if source.account_id == destination.account_id:
                    continue
                transactions.append(
                    Transaction(
                        stable_id(seed, "baseline-tx", tx_index),
                        source.account_id,
                        destination.account_id,
                        amount,
                        "USD",
                        "ACH",
                        SIMULATION_END - timedelta(days=days - day, hours=rng.randrange(24)),
                        "US",
                        None,
                    )
                )
                tx_index += 1
    return tuple(customers), tuple(accounts), tuple(transactions)
