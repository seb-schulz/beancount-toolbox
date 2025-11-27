"""Parse portfolio-weight directives from beancount entries.

This module provides functions to parse custom "portfolio-weight" directives
from beancount ledgers, with automatic bucket inference and date filtering.
"""
import typing
from datetime import date
from decimal import Decimal


def find_accounts_with_weights(
    custom_entries: typing.Sequence[typing.Any],
    end_date: date | None = None
) -> set[str]:
    """Build set of accounts that have weight directives.

    Args:
        custom_entries: List of Custom directive entries
        end_date: Optional cutoff date (directives after this are ignored)

    Returns:
        Set of account names with portfolio-weight directives

    Example:
        >>> entries = [custom1, custom2, custom3]
        >>> find_accounts_with_weights(entries, date(2024, 1, 1))
        {'Assets:US', 'Assets:US:ETrade:ITOT'}
    """
    accounts_with_weights = set()

    for entry in custom_entries:
        if entry.type != 'portfolio-weight':
            continue

        # Filter by date
        if end_date and entry.date > end_date:
            continue

        accounts_with_weights.add(entry.values[0].value)

    return accounts_with_weights


def infer_bucket(
    account: str,
    accounts_with_weights: set[str],
    root_account: str
) -> str:
    """Infer bucket for an account based on closest ancestor with directive.

    Args:
        account: The account to find bucket for
        accounts_with_weights: Set of accounts with weight directives
        root_account: Fallback root account

    Returns:
        Bucket account name (closest ancestor with directive, or root)

    Example:
        >>> infer_bucket(
        ...     'Assets:US:Vanguard:VTSAX',
        ...     {'Assets:US', 'Assets:US:Vanguard'},
        ...     'Assets:US'
        ... )
        'Assets:US:Vanguard'
    """
    bucket = root_account
    parts = account.split(':')

    # Walk up the hierarchy from immediate parent to root
    for i in range(len(parts) - 1, 0, -1):
        ancestor = ':'.join(parts[:i])
        if ancestor in accounts_with_weights:
            bucket = ancestor
            break

    return bucket


def parse_weight_directives(
    custom_entries: typing.Sequence[typing.Any],
    root_account: str,
    default_currency: str,
    end_date: date | None = None
) -> typing.Dict[str, typing.Dict[str, Decimal | tuple[Decimal, str]]]:
    """Parse all portfolio-weight directives into structured format.

    Args:
        custom_entries: List of Custom directive entries
        root_account: Root account for bucket inference
        default_currency: Operating currency for validation
        end_date: Optional cutoff date (directives after this are ignored)

    Returns:
        Dict mapping bucket -> account -> weight value
        Weight value is either:
        - Decimal: percentage (0.0 to 1.0)
        - tuple[Decimal, str]: (amount, currency)

    Raises:
        ValueError: If currency doesn't match default_currency

    Example:
        >>> parse_weight_directives(entries, 'Assets:US', 'USD')
        {
            'Assets:US': {
                'Assets:US:ETrade:ITOT': Decimal('0.6'),
                'Assets:US:Vanguard:Cash': (Decimal('5000'), 'USD')
            }
        }
    """
    # First pass: identify all accounts with directives
    accounts_with_weights = find_accounts_with_weights(custom_entries, end_date)

    # Second pass: parse directives and infer buckets
    weight_entries: typing.Dict[str, typing.Dict[str, Decimal | tuple]] = {}

    for entry in custom_entries:
        if entry.type != 'portfolio-weight':
            continue

        # Filter by date
        if end_date and entry.date > end_date:
            continue

        account = entry.values[0].value
        weight_value = entry.values[1]

        # Determine bucket
        if len(entry.values) >= 3:
            # Explicit bucket provided
            bucket = entry.values[2].value
        else:
            # Infer from closest ancestor with directive
            bucket = infer_bucket(account, accounts_with_weights, root_account)

        # Initialize bucket dict if needed
        weight_entries.setdefault(bucket, {})

        # Parse weight value (percentage or absolute amount)
        amount = getattr(weight_value, 'number', None)
        currency = getattr(weight_value, 'currency', None)

        if amount is not None and currency is not None:
            # Absolute amount - validate currency
            if currency != default_currency:
                raise ValueError(
                    f"Weight for '{account}' uses currency '{currency}', "
                    f"but only '{default_currency}' is allowed"
                )
            weight_entries[bucket][account] = (amount, currency)
        else:
            # Percentage
            weight_entries[bucket][account] = weight_value.value

    return weight_entries
