import typing
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from beancount.core import account_types
from fava import ext, internal_api
from fava.beans import protocols
from fava.context import g
from fava.core import charts, conversion, inventory, query, tree

from .weight_allocation import weight_list

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
]


class _Amount(typing.NamedTuple):
    number: Decimal
    currency: str


class _CustomWeight(typing.NamedTuple):
    account: str
    bucket: str
    weight: Decimal


@dataclass(frozen=True)
class Portfolio:
    """A portfolio.

    Consists of a title and the result table to render.
    """
    total: protocols.Amount
    table: query.QueryResultTable


def calculate_bucket_total(
    bucket: str,
    account_map: typing.Dict[str, tree.TreeNode],
    default_currency: str,
    ledger: typing.Any
) -> Decimal:
    """Calculate total value of a bucket in default currency.

    Args:
        bucket: The bucket account name
        account_map: Dict mapping account names to TreeNode objects
        default_currency: The operating currency
        ledger: The ledger object for price lookups

    Returns:
        Total value of bucket in default currency
    """
    if bucket not in account_map:
        raise ValueError(f"Bucket '{bucket}' not found in account tree")

    node = account_map[bucket]
    balance = node.balance_children

    # Convert to default currency using market prices
    simple_balance = balance.reduce(
        lambda p: conversion.get_market_value(
            p, ledger.prices, g.filtered.end_date)
    )

    return simple_balance.get(default_currency, Decimal(0))


def convert_amounts_to_percentages(
    weight_entries: typing.Dict[str, typing.Dict[str, Decimal | tuple]],
    account_map: typing.Dict[str, tree.TreeNode],
    default_currency: str,
    ledger: typing.Any
) -> typing.Dict[str, typing.Dict[str, Decimal]]:
    """Convert absolute amount weights to percentage weights.

    Args:
        weight_entries: Weights with mixed types (Decimal percentages or (amount, currency) tuples)
        account_map: Dict mapping account names to TreeNode objects
        default_currency: The operating currency
        ledger: The ledger object for price lookups

    Returns:
        Weight entries with all values converted to Decimal percentages

    Raises:
        ValueError: If absolute amount exceeds bucket total
    """
    converted = {}

    for bucket, weights in weight_entries.items():
        # Calculate bucket total once per bucket
        bucket_total = calculate_bucket_total(
            bucket, account_map, default_currency, ledger)

        converted[bucket] = {}

        for account, weight in weights.items():
            if isinstance(weight, tuple):
                # It's an absolute amount - convert to percentage
                amount, currency = weight

                if bucket_total == 0:
                    raise ValueError(
                        f"Cannot convert absolute amount for '{account}': "
                        f"bucket '{bucket}' has zero total value"
                    )

                percentage = amount / bucket_total

                if percentage > 1:
                    raise ValueError(
                        f"Absolute amount {amount} {currency} for '{account}' "
                        f"exceeds bucket '{bucket}' total of {bucket_total} {default_currency} "
                        f"(would be {percentage * 100:.2f}%)"
                    )

                converted[bucket][account] = percentage
            else:
                # It's already a percentage - keep as is
                converted[bucket][account] = weight

    return converted


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

    # Build map of which accounts have weight directives
    accounts_with_weights = set()
    for x in ledger.all_entries_by_type.Custom:
        if x.type == 'portfolio-weight':
            # Only consider directives on or before end_date
            if g.filtered.end_date and x.date > g.filtered.end_date:
                continue
            accounts_with_weights.add(x.values[0].value)

    # Parse directives with automatic bucket inference
    weight_entries = {}
    for x in ledger.all_entries_by_type.Custom:
        if x.type != 'portfolio-weight':
            continue

        # Only consider directives on or before end_date
        if g.filtered.end_date and x.date > g.filtered.end_date:
            continue

        account = x.values[0].value
        weight_value = x.values[1]

        # Determine bucket
        if len(x.values) >= 3:
            # Explicit bucket provided
            bucket = x.values[2].value
        else:
            # No explicit bucket - find closest ancestor with directive
            bucket = root_account  # Default
            parts = account.split(':')
            for i in range(len(parts) - 1, 0, -1):
                ancestor = ':'.join(parts[:i])
                if ancestor in accounts_with_weights:
                    bucket = ancestor
                    break

        weight_entries.setdefault(bucket, {})

        amount = getattr(weight_value, 'number', None)
        currency = getattr(weight_value, 'currency', None)
        if amount is not None and currency is not None:
            if currency != default_currency:
                raise ValueError(
                    f"Weight for '{account}' uses currency '{currency}', "
                    f"but only '{default_currency}' is allowed"
                )
            weight_entries[bucket][account] = (amount, currency)
        else:
            weight_entries[bucket][account] = weight_value.value

    # Build account map for conversion (needed to access node balances)
    account_map = {}

    def build_map(node):
        account_map[node.name] = node
        for child in node.children:
            build_map(child)
    build_map(root_node)

    # Convert any absolute amount weights to percentages
    weight_entries = convert_amounts_to_percentages(
        weight_entries, account_map, default_currency, ledger
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

        currency = account_currencies[account][0]
        price_per_unit = ledger.prices.get_price(
            (currency, default_currency), g.filtered.end_date) if len(account_currencies[node.name]) > 0 else None

        account_balances.append(Row(
            account=node.name,
            balance=node.balance,
            weight=weights[account],
            price_per_unit=price_per_unit,
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
                    row.quantity_delta(total)
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
