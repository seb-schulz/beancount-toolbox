__plugins__ = ['spread_pad']

from beancount.core import data, flags, realization, amount, inventory
from beancount.utils import date_utils
from datetime import date
from beancount.utils import misc_utils
from collections import namedtuple
from fava.beans import abc

SpreadPadError = namedtuple('SpreadPadError', 'source message entry')


class CustomPad:

    def __init__(self, entry):
        self._entry: abc.Custom = entry

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

    @property
    def total_amount(self):
        return self._entry.values[2].value

    def has_total_amount(self):
        return len(self._entry.values
                   ) > 2 and self._entry.values[2].dtype == amount.Amount


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
    gap = {
        'd': lambda x: int(x),
        'w': lambda x: int(x) * 7,
    }[freq[-1]](freq[:-1])

    dates = [
        dt for i, dt in enumerate(date_utils.iter_dates(start, end))
        if i % gap == gap - 1
    ]
    remains = amount.sub(expected_balance, current_balance)

    if abs(remains.number) <= data.D('0.001'):
        raise ValueError(f"Cannot spread {remains}")

    r = []
    for idx, current_date in enumerate(dates, start=1):
        amount_ = amount.Amount(
            round(remains.number / (amount.D(len(dates) - idx + 1)), 2),
            remains.currency,
        )
        remains = amount.sub(remains, amount_)
        narration = f"(Padding inserted for Balance of {expected_balance} for difference {amount_} [{idx} / {len(dates)}])"
        r.append(
            data.Transaction(
                dict(**meta), current_date, flags.FLAG_PADDING, None,
                narration, data.EMPTY_SET, data.EMPTY_SET, [
                    data.create_simple_posting(None, account, amount_.number,
                                               amount_.currency),
                    data.create_simple_posting(None, source_account,
                                               -amount_.number,
                                               amount_.currency),
                ]))
    return r


def spread_pad(entries, options_map):
    errors = []
    # Find all the pad entries and group them by account.
    pad = [
        CustomPad(e) for e in misc_utils.filter_type(entries, data.Custom)
        if e.type == 'pad'
    ]
    pad_dict = misc_utils.groupby(lambda x: x.account, pad)

    # Partially realize the postings, so we can iterate them by account.
    by_account = realization.postings_by_account(entries)

    additionals = []
    for account in pad_dict.keys() & by_account.keys():
        account_balance = inventory.Inventory()
        first_directive = None
        eligable_pad = None

        for entry_or_txn_posting in by_account[account]:
            if isinstance(entry_or_txn_posting,
                          data.Custom) and entry_or_txn_posting.type == 'pad':
                eligable_pad = CustomPad(entry_or_txn_posting)
            elif isinstance(entry_or_txn_posting, data.Open):
                first_directive = entry_or_txn_posting
            elif isinstance(entry_or_txn_posting, data.TxnPosting):
                account_balance.add_position(entry_or_txn_posting.posting)
            elif isinstance(entry_or_txn_posting,
                            data.Balance) and eligable_pad is None:
                first_directive = entry_or_txn_posting
            elif isinstance(
                    entry_or_txn_posting, data.Balance
            ) and eligable_pad is not None and account == eligable_pad.account:
                try:
                    for e in create_pads(
                            first_directive.date,
                            entry_or_txn_posting.date,
                            account_balance.get_currency_units(
                                entry_or_txn_posting.amount.currency),
                            entry_or_txn_posting.amount,
                            meta=eligable_pad.meta.copy(),
                            account=eligable_pad.account,
                            source_account=eligable_pad.source_account,
                            freq=eligable_pad.meta.get('frequency', '1d')):
                        account_balance.add_position(e.postings[0])
                        additionals.append(e)
                except ValueError as e:
                    errors.append(
                        SpreadPadError(eligable_pad.meta, e,
                                       entry_or_txn_posting))
                first_directive = entry_or_txn_posting
                eligable_pad = None

    return data.sorted(entries + additionals), errors
