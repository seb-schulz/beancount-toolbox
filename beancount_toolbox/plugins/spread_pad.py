"""Spread Pad Plugin - Distribute padding entries across multiple days.

This plugin spreads padding amounts across multiple days with consistent
base amounts and the remainder in the last entry.

Recommended plugin configuration:
    option "plugin_processing_mode" "raw"

    ; PLUGINS_POST
    plugin "beancount.ops.pad"
    plugin "beancount_toolbox.plugins.spread_pad"
    plugin "beancount.ops.balance"

Usage:
    2021-01-01 balance Assets:Cash 100.00 EUR
    2021-01-05 custom "pad" Assets:Cash Expenses:Misc
    2021-01-10 balance Assets:Cash 80.00 EUR

This will create padding entries on days 2021-01-06 through 2021-01-09
distributing the -20.00 EUR difference with consistent amounts (-5.00 each).
"""

__plugins__ = ['spread_pad']

from collections import namedtuple
from datetime import date, timedelta
from decimal import Decimal

from beancount.core import amount, data, flags, inventory, realization
from beancount.utils import misc_utils

SpreadPadError = namedtuple('SpreadPadError', 'source message entry')


def iter_dates(start_date, end_date):
    """Yield all the dates between 'start_date' and 'end_date'.

    Args:
      start_date: An instance of datetime.date.
      end_date: An instance of datetime.date.
    Yields:
      Instances of datetime.date.
    """
    oneday = timedelta(days=1)
    date = start_date
    while date < end_date:
        yield date
        date += oneday


class CustomPad:
    def __init__(self, entry):
        self._entry = entry

    def __str__(self) -> str:
        from beancount.parser import printer
        return printer.format_entry(self._entry)

    @property
    def meta(self):
        return self._entry.meta

    @property
    def date(self):
        return self._entry.date

    @property
    def account(self):
        return self._entry.values[0].value

    @property
    def source_account(self):
        return self._entry.values[1].value


PadPeriod = namedtuple('PadPeriod', [
    'start_directive',   # data.Open or data.Balance (period start)
    'pad_directive',     # CustomPad instance
    'end_balance',       # data.Balance (period end)
])


def create_pads(
    start: date,
    end: date,
    current_balance: amount.Amount,
    expected_balance: amount.Amount,
    *,
    meta: dict,
    account: data.Account,
    source_account: data.Account,
    freq: str = '1d',
):
    # Always use expected_balance for narration
    narration_balance = expected_balance
    gap = {
        'd': lambda x: int(x),
        'w': lambda x: int(x) * 7,
    }[freq[-1]](freq[:-1])

    dates = [
        dt for i, dt in enumerate(iter_dates(start, end))
        if i % gap == gap - 1
    ]
    remains = amount.sub(expected_balance, current_balance)

    if remains.number is None:
        raise ValueError(f"Number {remains} is none")

    if abs(remains.number) <= Decimal('0.001'):
        raise ValueError(f"Cannot spread {remains}")

    # Calculate base amount once for consistency (production behavior)
    # All entries except the last get this base amount, ensuring clean distribution
    base_value = (remains.number / Decimal(len(dates))
                  ).quantize(Decimal('0.01'))

    r = []
    for idx, current_date in enumerate(dates, start=1):
        if remains.number is None:
            raise ValueError(f"Number {remains} is none")

        if idx < len(dates):
            # Use base amount for all entries except last
            amount_ = amount.Amount(base_value, remains.currency)
        else:
            # Last entry gets exact remainder to ensure perfect total
            amount_ = remains

        remains = amount.sub(remains, amount_)
        narration = f"(Padding inserted for Balance of {narration_balance} for difference {amount_} [{idx} / {len(dates)}])"

        t = data.Transaction(
            dict(**meta), current_date, flags.FLAG_PADDING, None,
            narration, data.EMPTY_SET, data.EMPTY_SET, [])

        if amount_.number is None:
            raise ValueError(f"Number {amount_} is none")

        data.create_simple_posting(
            t, account, amount_.number, amount_.currency)
        data.create_simple_posting(
            t, source_account, -amount_.number, amount_.currency)

        number = remains.number
        r.append(t)
    return r


def process_account_entries(
    account: str,
    entries_for_account: list,
    errors: list,
) -> list[data.Transaction]:
    """Process entries for one account and generate padding transactions.

    State machine per account:
        [Open/Balance] → [custom "pad"] → [Balance]
         ^period_start    ^pending          ^trigger

    Padding is calculated based only on the difference between:
    - current_balance (from account_balance tracking)
    - expected_balance (from the end Balance directive)

    Args:
        account: Account name being processed
        entries_for_account: Chronological entries for this account
        errors: List to append SpreadPadError instances

    Returns:
        List of generated padding Transaction entries
    """
    account_balance = inventory.Inventory()
    period_start_directive = None
    pending_pad = None
    padding_transactions = []

    for entry_or_txn_posting in entries_for_account:
        # Branch 1: Custom "pad" directive
        if isinstance(entry_or_txn_posting, data.Custom) and entry_or_txn_posting.type == 'pad':
            pending_pad = CustomPad(entry_or_txn_posting)

        # Branch 2: Open directive (potential period start)
        elif isinstance(entry_or_txn_posting, data.Open):
            period_start_directive = entry_or_txn_posting

        # Branch 3: Transaction posting (update balance)
        elif isinstance(entry_or_txn_posting, data.TxnPosting):
            account_balance.add_position(entry_or_txn_posting.posting)

        # Branch 4: Balance without pending pad (potential period start)
        elif isinstance(entry_or_txn_posting, data.Balance) and pending_pad is None:
            period_start_directive = entry_or_txn_posting

        # Branch 5: Balance with pending pad (TRIGGER - generate padding)
        elif isinstance(entry_or_txn_posting, data.Balance) and pending_pad is not None and account == pending_pad.account:
            if period_start_directive is None:
                raise ValueError("period_start_directive must be Open or Balance")

            # Calculate padding based only on balance difference
            current_balance = account_balance.get_currency_units(
                entry_or_txn_posting.amount.currency)
            expected_balance = entry_or_txn_posting.amount

            # Generate padding entries
            try:
                generated_pads = create_pads(
                    period_start_directive.date,
                    entry_or_txn_posting.date,
                    current_balance,
                    expected_balance,
                    meta=dict(**pending_pad.meta),
                    account=pending_pad.account,
                    source_account=pending_pad.source_account,
                    freq=str(pending_pad.meta.get('frequency', '1d')),
                )

                # Update balance and collect entries
                for pad_entry in generated_pads:
                    account_balance.add_position(pad_entry.postings[0])
                    padding_transactions.append(pad_entry)

            except ValueError as e:
                errors.append(
                    SpreadPadError(pending_pad.meta, e, entry_or_txn_posting)
                )

            # Reset state for next period
            period_start_directive = entry_or_txn_posting
            pending_pad = None

    return padding_transactions


def spread_pad(entries, options_map):
    """Spread padding entries across multiple days between balance directives.

    This plugin processes custom "pad" directives between two balance directives.
    The "two balance directive" constraint is enforced per account:
    - Balance/Open marks period start
    - Custom "pad" marks pending padding
    - Next Balance triggers padding generation

    Padding is calculated based only on the difference between the current
    account balance and the expected balance from the Balance directive.

    Args:
        entries: List of beancount entries
        options_map: Beancount options

    Returns:
        Tuple of (entries with padding added, list of errors)
    """
    errors = []

    # Find all custom "pad" entries, grouped by account
    custom_pads = [
        CustomPad(e) for e in misc_utils.filter_type(entries, data.Custom)
        if e.type == 'pad'
    ]
    pad_accounts = misc_utils.groupby(lambda x: x.account, custom_pads)

    # Get entries organized by account (chronologically)
    by_account = realization.postings_by_account(entries)

    # Process each account that has custom pads
    all_padding_transactions = []
    for account in pad_accounts.keys() & by_account.keys():
        padding_transactions = process_account_entries(
            account,
            by_account[account],
            errors,
        )
        all_padding_transactions.extend(padding_transactions)

    # Merge and sort all entries
    return data.sorted(entries + all_padding_transactions), errors
