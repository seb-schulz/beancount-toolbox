from fava.context import g
from fava.ext import FavaExtensionBase
from fava.core import conversion
import dataclasses
import typing
from decimal import Decimal

from fava.beans import create
from beancount.core import amount, account_types
from fava.beans.types import BeancountOptions
from beancount.parser import options
from fava.core import budgets
from functools import reduce
from flask_babel import gettext  # type: ignore[import-untyped]


class Row(typing.NamedTuple):
    """A row in the portfolio tables."""

    account: str
    balance: Decimal | None


@dataclasses.dataclass
class Portfolio:
    """A portfolio."""

    title: str
    rows: list[Row]
    types = (
        ("account", str),
        ("balance", amount.Amount),

    )


def _convert_to_amount(value: dict[str, Decimal], options: BeancountOptions) -> amount.Amount | None:
    currency = options['operating_currency'][0]
    try:
        return amount.Amount(value[currency], currency)
    except KeyError:
        pass


class BudgetPlan(FavaExtensionBase):
    report_title = 'Budget Plan'

    def budget_plan(self):
        if g.filtered.date_range is None:
            return []

        root = g.filtered.root_tree

        b, err = budgets.parse_budgets(self.ledger.all_entries_by_type.Custom)

        acctypes = options.get_account_types(self.ledger.options)

        rows = [x for x in [
            Row(
                a,
                _convert_to_amount(budgets.calculate_budget_children(
                    b, a, g.filtered.date_range.begin, g.filtered.date_range.end,
                ), self.ledger.options),
            )

            for a in root.accounts if account_types.is_income_statement_account(
                a, acctypes,
            )
        ] if x.balance is not None]

        rows.append(Row(gettext('Net Profit'), reduce(
            amount.add, [x.balance for x in rows])))

        return [
            Portfolio(
                title=f"Budget for the period {
                    g.filtered.date_range.begin} - {g.filtered.date_range.end}",
                rows=rows,
            )
        ]
