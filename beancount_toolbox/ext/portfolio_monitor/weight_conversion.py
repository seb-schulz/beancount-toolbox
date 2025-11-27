"""Convert absolute amount weights to percentage weights.

This module handles conversion of monetary amount weights (e.g., 5000 USD)
to percentage weights (e.g., 0.25 for 25%) based on bucket totals.
"""
import typing
from decimal import Decimal


def calculate_bucket_total(
    balance_children: typing.Any,  # CounterInventory
    default_currency: str,
    price_lookup: typing.Callable[[typing.Any], typing.Any]
) -> Decimal:
    """Calculate total value of a bucket in default currency.

    This function is designed to be called with injected dependencies,
    avoiding direct dependency on Flask context.

    Args:
        balance_children: The balance_children inventory from TreeNode
        default_currency: The operating currency
        price_lookup: Function to convert prices to market value
                     Signature: (position) -> converted_value

    Returns:
        Total value of bucket in default currency

    Example:
        >>> # With Flask context:
        >>> from fava.core import conversion
        >>> lookup = lambda p: conversion.get_market_value(p, ledger.prices, g.filtered.end_date)
        >>> calculate_bucket_total(node.balance_children, 'USD', lookup)
        Decimal('10000.00')
    """
    # Convert to default currency using market prices
    simple_balance = balance_children.reduce(price_lookup)
    return simple_balance.get(default_currency, Decimal(0))


def convert_amounts_to_percentages(
    weight_entries: typing.Dict[str, typing.Dict[str, Decimal | tuple]],
    account_map: typing.Dict[str, typing.Any],  # Dict[str, TreeNode]
    default_currency: str,
    price_lookup: typing.Callable[[typing.Any], typing.Any]
) -> typing.Dict[str, typing.Dict[str, Decimal]]:
    """Convert absolute amount weights to percentage weights.

    This is the core conversion logic, isolated from Flask dependencies.
    The price_lookup function is injected, allowing the caller to provide
    the appropriate context.

    Args:
        weight_entries: Weights with mixed types (Decimal percentages or (amount, currency) tuples)
        account_map: Dict mapping account names to TreeNode objects
        default_currency: The operating currency
        price_lookup: Function to convert prices to market value
                     Signature: (position) -> converted_value

    Returns:
        Weight entries with all values converted to Decimal percentages

    Raises:
        ValueError: If bucket not found in account_map
        ValueError: If absolute amount exceeds bucket total
        ValueError: If bucket has zero total for absolute amount conversion

    Example:
        >>> weight_entries = {
        ...     'Assets:US': {
        ...         'Assets:US:Cash': (Decimal('5000'), 'USD'),
        ...         'Assets:US:Stocks': Decimal('0.6')
        ...     }
        ... }
        >>> # Assuming bucket total is 10000 USD
        >>> convert_amounts_to_percentages(weight_entries, account_map, 'USD', price_lookup)
        {
            'Assets:US': {
                'Assets:US:Cash': Decimal('0.5'),
                'Assets:US:Stocks': Decimal('0.6')
            }
        }
    """
    converted = {}

    for bucket, weights in weight_entries.items():
        # Validate bucket exists
        if bucket not in account_map:
            raise ValueError(f"Bucket '{bucket}' not found in account tree")

        node = account_map[bucket]

        # Calculate bucket total once per bucket
        bucket_total = calculate_bucket_total(
            node.balance_children,
            default_currency,
            price_lookup
        )

        converted[bucket] = {}

        for account, weight in weights.items():
            if isinstance(weight, tuple):
                # Absolute amount - convert to percentage
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
                # Already a percentage
                converted[bucket][account] = weight

    return converted
