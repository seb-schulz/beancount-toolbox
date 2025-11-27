import typing
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from beancount.core import account_types
from fava import ext
from fava.beans import protocols
from fava.context import g
from fava.core import conversion, inventory, query

from .weight_allocation import weight_list
from .weight_conversion import convert_amounts_to_percentages
from .weight_parsing import parse_weight_directives

if typing.TYPE_CHECKING:  # pragma: no cover
    from flask.wrappers import Response

TABLE_HEADER = [
    query.StrColumn("account"),
    query.InventoryColumn("Balance"),
    query.InventoryColumn("Units"),
    query.InventoryColumn("Price per Units"),
    query.InventoryColumn("Current Allocation"),
    query.InventoryColumn("Target Allocation"),
    query.InventoryColumn("Amount Delta"),
    query.InventoryColumn("Quantity Delta"),
    query.DateColumn("Last Price Date"),
]


class _Amount(typing.NamedTuple):
    number: Decimal
    currency: str


@dataclass(frozen=True)
class Portfolio:
    """A portfolio.

    Consists of a title and the result table to render.
    """
    total: protocols.Amount
    table: query.QueryResultTable


def to_pct(val: Decimal | None) -> inventory.SimpleCounterInventory:
    inv = inventory.SimpleCounterInventory()
    if val is not None:
        inv.add('%', round(val * 100, 2))
    return inv


def to_default_currency(inv) -> Decimal:
    currency = g.ledger.options["operating_currency"][0]
    return inv.get(currency, Decimal(0))


def to_inventory(val: Decimal | None, currency: str) -> inventory.SimpleCounterInventory:
    inv = inventory.SimpleCounterInventory()
    if val is not None:
        inv.add(currency, val)
    return inv


@dataclass(frozen=True)
class Row:
    account: str
    balance: inventory.CounterInventory
    currency: str
    price_per_unit: Decimal | None
    price_date: date | None = None
    weight: Decimal | None = None

    @property
    def simple_balance(self) -> inventory.SimpleCounterInventory:
        return self.balance.reduce(lambda p: conversion.get_market_value(
            p, g.ledger.prices, g.filtered.end_date))

    @property
    def units(self) -> inventory.SimpleCounterInventory:
        return conversion.units(self.balance)

    @property
    def target_allocation(self) -> Decimal | None:
        if self.weight is not None:
            return self.weight

    def current_allocation(self, total: Decimal) -> Decimal | None:
        if self.balance is not None:
            return to_default_currency(self.simple_balance) / total

    def amount_delta(self, total: Decimal) -> inventory.SimpleCounterInventory:
        ca = (self.current_allocation(total) or Decimal(0)) * total
        ta = (self.target_allocation or Decimal(0)) * total

        inv = inventory.SimpleCounterInventory()
        inv.add(
            g.ledger.options["operating_currency"][0], ta - ca
        )
        return inv

    def quantity_delta(self, total: Decimal) -> inventory.SimpleCounterInventory:
        ca = (self.current_allocation(total) or Decimal(0)) * total
        ta = (self.target_allocation or Decimal(0)) * total
        delta = ta - ca

        inv = inventory.SimpleCounterInventory()
        if self.price_per_unit is not None:
            units = delta / self.price_per_unit
            inv.add(self.currency, units)
        return inv


def portfolio(config: typing.Any, filter_str: str | None = None) -> Portfolio:
    """Get an account tree based on matching regex patterns."""
    tree = g.filtered.root_tree
    ledger = g.filtered.ledger
    default_currency = ledger.options["operating_currency"][0]
    root_account = config.get('root_account', ledger.options["name_assets"])

    root_node = None
    assets = ledger.options["name_assets"]
    for account, node in tree.items():
        if account == root_account and account_types.is_account_type(assets, account):
            root_node = node
            break
    if root_node is None:
        raise ValueError("root node not found")

    if root_node.balance_children.is_empty():
        return Portfolio(_Amount(Decimal(0), default_currency), query.QueryResultTable(TABLE_HEADER, []))

    # Parse weight directives from ledger
    weight_entries = parse_weight_directives(
        ledger.all_entries_by_type.Custom,
        root_account,
        default_currency,
        g.filtered.end_date
    )

    # Build account map for conversion (needed to access node balances)
    account_map = {}

    def build_map(node):
        account_map[node.name] = node
        for child in node.children:
            build_map(child)
    build_map(root_node)

    # Convert any absolute amount weights to percentages
    # Create price lookup closure to inject Flask context
    def price_lookup(position):
        return conversion.get_market_value(position, ledger.prices, g.filtered.end_date)

    weight_entries = convert_amounts_to_percentages(
        weight_entries, account_map, default_currency, price_lookup
    )

    weights = weight_list(root_node, weight_entries)

    default_currency = ledger.options["operating_currency"][0]
    account_balances: list[Row] = []
    total = Decimal()

    account_currencies = {
        x.account: x.currencies for x in ledger.all_entries_by_type.Open}

    for account, node in tree.items():
        if account not in weights:
            continue

        if account not in account_currencies or not account_currencies[account]:
            raise ValueError(
                f"Account '{account}' has no currencies in its Open directive. "
                f"Please specify at least one currency: YYYY-MM-DD open {account} <CURRENCY>"
            )

        currency = account_currencies[account][0]
        price_per_unit = None
        price_date = None
        if len(account_currencies[node.name]) > 0:
            price_date, price_per_unit = ledger.prices.get_price_point(
                (currency, default_currency), g.filtered.end_date)
            if price_per_unit is None:
                price_date = None

        account_balances.append(Row(
            account=node.name,
            balance=node.balance,
            weight=weights[account],
            price_per_unit=price_per_unit,
            price_date=price_date,
            currency=currency,
        ))
        total += to_default_currency(account_balances[-1].simple_balance)

    return Portfolio(
        total=_Amount(number=total, currency=default_currency),
        table=query.QueryResultTable(
            TABLE_HEADER,
            [
                (
                    row.account,
                    row.simple_balance,
                    row.units,
                    to_inventory(row.price_per_unit, default_currency),
                    to_pct(row.current_allocation(total)),
                    to_pct(row.target_allocation),
                    row.amount_delta(total),
                    row.quantity_delta(total),
                    row.price_date,
                )
                for row in account_balances
            ],
        ))


class PortfolioMonitor(ext.FavaExtensionBase):

    report_title = "Portfolio Monitor"

    def portfolio(
        self,
        filter_str: str | None = None,
    ) -> Portfolio:
        """Get an account tree based on matching regex patterns."""
        return portfolio(self.config, filter_str)
