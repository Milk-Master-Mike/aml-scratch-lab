from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from itertools import pairwise

from engine.aml.controls import ControlDefinition
from engine.models import Alert, ScenarioDataset, Transaction


def _alert(
    control: ControlDefinition,
    account_id: str,
    conditions: tuple[str, ...],
    transactions: list[Transaction],
) -> Alert:
    return Alert(
        control.id,
        account_id,
        control.severity,
        conditions,
        tuple(tx.transaction_id for tx in transactions),
    )


def evaluate(control: ControlDefinition, dataset: ScenarioDataset) -> Alert | None:
    if not control.enabled:
        return None
    return EVALUATORS[control.evaluator](control, dataset)


def evaluate_rapid_movement(
    control: ControlDefinition, transactions: tuple[Transaction, ...]
) -> Alert | None:
    """M1-compatible adapter for callers that only supply transactions."""
    empty = ScenarioDataset("compat", "compat", 0, (), (), transactions, False, None)
    return _rapid_movement(control, empty)


def _rapid_movement(control: ControlDefinition, dataset: ScenarioDataset) -> Alert | None:
    incoming: dict[str, list[Transaction]] = defaultdict(list)
    outgoing: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in dataset.transactions:
        view = transaction.monitoring_view()
        if view["destination_account"]:
            incoming[view["destination_account"]].append(transaction)
        if view["source_account"]:
            outgoing[view["source_account"]].append(transaction)
    minimum = Decimal(str(control.conditions.minimum_incoming))
    ratio = Decimal(str(control.conditions.outgoing_ratio))
    for account_id, credits in incoming.items():
        for credit in credits:
            cutoff = credit.timestamp + timedelta(hours=control.conditions.window_hours or 24)
            debits = [
                tx for tx in outgoing[account_id] if credit.timestamp <= tx.timestamp <= cutoff
            ]
            if (
                credit.amount >= minimum
                and sum((tx.amount for tx in debits), Decimal()) >= credit.amount * ratio
                and len({tx.destination_account for tx in debits})
                >= (control.conditions.minimum_counterparties or 1)
            ):
                return _alert(
                    control,
                    account_id,
                    ("minimum_incoming", "outgoing_ratio", "minimum_counterparties"),
                    [credit, *debits],
                )
    return None


def _abnormal_velocity(control: ControlDefinition, dataset: ScenarioDataset) -> Alert | None:
    outgoing: dict[str, list[Transaction]] = defaultdict(list)
    for tx in dataset.transactions:
        if tx.source_account:
            outgoing[tx.source_account].append(tx)
    window = timedelta(hours=control.conditions.window_hours or 1)
    minimum = control.conditions.minimum_transactions or 1
    for account_id, transactions in outgoing.items():
        ordered = sorted(transactions, key=lambda item: item.timestamp)
        for start in ordered:
            windowed = [
                tx for tx in ordered if start.timestamp <= tx.timestamp <= start.timestamp + window
            ]
            if len(windowed) >= minimum:
                return _alert(
                    control, account_id, ("minimum_transactions", "window_hours"), windowed
                )
    return None


def _profile_volume(control: ControlDefinition, dataset: ScenarioDataset) -> Alert | None:
    account_customer = {account.account_id: account.customer_id for account in dataset.accounts}
    expected = {
        customer.customer_id: customer.expected_monthly_volume for customer in dataset.customers
    }
    totals: dict[str, Decimal] = defaultdict(Decimal)
    relevant: dict[str, list[Transaction]] = defaultdict(list)
    for tx in dataset.transactions:
        if tx.destination_account in account_customer:
            totals[tx.destination_account] += tx.amount
            relevant[tx.destination_account].append(tx)
    multiplier = Decimal(str(control.conditions.volume_multiplier))
    for account_id, total in totals.items():
        if total >= expected[account_customer[account_id]] * multiplier:
            condition = (
                "customer_profile_volume"
                if control.evaluator == "profile_mismatch"
                else "volume_deviation"
            )
            return _alert(
                control, account_id, (condition, "volume_multiplier"), relevant[account_id]
            )
    return None


def _funnel_activity(control: ControlDefinition, dataset: ScenarioDataset) -> Alert | None:
    incoming: dict[str, list[Transaction]] = defaultdict(list)
    outgoing: dict[str, list[Transaction]] = defaultdict(list)
    for tx in dataset.transactions:
        if tx.destination_account:
            incoming[tx.destination_account].append(tx)
        if tx.source_account:
            outgoing[tx.source_account].append(tx)
    ratio = Decimal(str(control.conditions.outgoing_ratio))
    for account_id, credits in incoming.items():
        for first in credits:
            cutoff = first.timestamp + timedelta(hours=control.conditions.window_hours or 24)
            windowed = [tx for tx in credits if first.timestamp <= tx.timestamp <= cutoff]
            sources = {tx.source_account for tx in windowed}
            total = sum((tx.amount for tx in windowed), Decimal())
            if len(sources) < (control.conditions.minimum_sources or 1) or total < Decimal(
                str(control.conditions.minimum_incoming)
            ):
                continue
            debits = [
                tx for tx in outgoing[account_id] if first.timestamp <= tx.timestamp <= cutoff
            ]
            if sum((tx.amount for tx in debits), Decimal()) >= total * ratio:
                return _alert(
                    control,
                    account_id,
                    ("minimum_sources", "consolidated_outflow"),
                    [*windowed, *debits],
                )
    return None


def _circular_flow(control: ControlDefinition, dataset: ScenarioDataset) -> Alert | None:
    by_source: dict[str, list[Transaction]] = defaultdict(list)
    for tx in dataset.transactions:
        if tx.source_account and tx.destination_account:
            by_source[tx.source_account].append(tx)
    hops = control.conditions.minimum_hops or 3
    window = timedelta(hours=control.conditions.window_hours or 24)
    minimum = Decimal(str(control.conditions.minimum_amount))
    for start in dataset.transactions:
        if not start.source_account or not start.destination_account or start.amount < minimum:
            continue
        path = [start]
        origin, current = start.source_account, start.destination_account
        while len(path) < hops:
            candidates = [
                tx
                for tx in by_source[current]
                if path[-1].timestamp < tx.timestamp <= start.timestamp + window
                and tx.amount >= minimum
            ]
            if not candidates:
                break
            next_tx = min(candidates, key=lambda item: item.timestamp)
            path.append(next_tx)
            current = next_tx.destination_account or ""
        if len(path) >= hops and current == origin:
            return _alert(control, origin, ("closed_loop", "minimum_hops"), path)
    return None


def _dormant_activation(control: ControlDefinition, dataset: ScenarioDataset) -> Alert | None:
    by_account: dict[str, list[Transaction]] = defaultdict(list)
    for tx in dataset.transactions:
        for account_id in (tx.source_account, tx.destination_account):
            if account_id:
                by_account[account_id].append(tx)
    dormant = timedelta(days=control.conditions.dormant_days or 180)
    amount = Decimal(str(control.conditions.activation_amount))
    for account_id, transactions in by_account.items():
        ordered = sorted(transactions, key=lambda item: item.timestamp)
        for previous, current in pairwise(ordered):
            if current.timestamp - previous.timestamp >= dormant and current.amount >= amount:
                return _alert(
                    control,
                    account_id,
                    ("dormancy_period", "activation_amount"),
                    [previous, current],
                )
    return None


EVALUATORS = {
    "rapid_movement": _rapid_movement,
    "abnormal_velocity": _abnormal_velocity,
    "volume_deviation": _profile_volume,
    "funnel_activity": _funnel_activity,
    "circular_flow": _circular_flow,
    "dormant_activation": _dormant_activation,
    "profile_mismatch": _profile_volume,
}
