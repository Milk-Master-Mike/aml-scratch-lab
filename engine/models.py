from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Customer:
    customer_id: str
    synthetic_name: str
    customer_type: str
    occupation_business_type: str
    risk_level: str
    country: str
    expected_monthly_volume: Decimal
    opened_at: datetime
    seed_id: int


@dataclass(frozen=True)
class Account:
    account_id: str
    customer_id: str
    account_type: str
    opened_at: datetime
    status: str
    balance: Decimal


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    source_account: str | None
    destination_account: str | None
    amount: Decimal
    currency: str
    transaction_type: str
    timestamp: datetime
    geography: str
    scenario_id: str | None

    def monitoring_view(self) -> dict:
        data = asdict(self)
        data.pop("scenario_id")
        return data


@dataclass(frozen=True)
class Alert:
    control_id: str
    account_id: str
    severity: str
    triggered_conditions: tuple[str, ...]
    transaction_ids: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioDataset:
    scenario_key: str
    scenario_id: str
    seed: int
    customers: tuple[Customer, ...]
    accounts: tuple[Account, ...]
    transactions: tuple[Transaction, ...]
    expected_alert: bool
    expected_severity: str | None
