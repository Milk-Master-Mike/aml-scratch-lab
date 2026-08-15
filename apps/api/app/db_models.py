from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.database import Base


class CustomerRow(Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    synthetic_name: Mapped[str] = mapped_column(String(160))
    customer_type: Mapped[str] = mapped_column(String(32))
    occupation_business_type: Mapped[str] = mapped_column(String(120))
    risk_level: Mapped[str] = mapped_column(String(16))
    country: Mapped[str] = mapped_column(String(2))
    expected_monthly_volume: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    seed_id: Mapped[int] = mapped_column(Integer)


class AccountRow(Base):
    __tablename__ = "accounts"
    account_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    account_type: Mapped[str] = mapped_column(String(32))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class ScenarioRow(Base):
    __tablename__ = "scenarios"
    scenario_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON)


class ControlRow(Base):
    __tablename__ = "controls"
    control_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean)
    definition: Mapped[dict] = mapped_column(JSON)


class ControlVersionRow(Base):
    __tablename__ = "control_versions"
    control_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    definition: Mapped[dict] = mapped_column(JSON)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RegressionBatchRow(Base):
    __tablename__ = "regression_batches"
    batch_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    seed: Mapped[int] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    untested: Mapped[int] = mapped_column(Integer, default=0)
    coverage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    mutation: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class TransactionRow(Base):
    __tablename__ = "transactions"
    transaction_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_account: Mapped[str | None] = mapped_column(String(36), nullable=True)
    destination_account: Mapped[str | None] = mapped_column(String(36), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3))
    transaction_type: Mapped[str] = mapped_column(String(24))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    geography: Mapped[str] = mapped_column(String(16))
    scenario_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class TestRunRow(Base):
    __tablename__ = "test_runs"
    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.scenario_id"))
    control_id: Mapped[str] = mapped_column(ForeignKey("controls.control_id"))
    seed: Mapped[int] = mapped_column(Integer)
    expected_alert: Mapped[bool] = mapped_column(Boolean)
    actual_alert: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    result: Mapped[str] = mapped_column(String(8))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict] = mapped_column(JSON)
    batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("regression_batches.batch_id"), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AlertRow(Base):
    __tablename__ = "alerts"
    alert_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.run_id"), unique=True)
    control_id: Mapped[str] = mapped_column(ForeignKey("controls.control_id"))
    account_id: Mapped[str] = mapped_column(String(36))
    severity: Mapped[str] = mapped_column(String(16))
    triggered_conditions: Mapped[list] = mapped_column(JSON)
    transaction_ids: Mapped[list] = mapped_column(JSON)
    disposition: Mapped[str] = mapped_column(Text, default="Human review required")
