import dataclasses
import json
import typing
from decimal import Decimal

from beancount.core import account_types, amount
from beancount.parser import options
from fava.context import g
from fava.core import budgets, number
from fava.ext import FavaExtensionBase
from flask_babel import gettext  # type: ignore[import-untyped]


@dataclasses.dataclass
class BudgetPosition:
    name: str
    positions: typing.Dict[str, Decimal]
    children: typing.Dict[str, 'BudgetPosition']


def BudgetPlanEncoder(format_decimal: number.DecimalFormatModule):
    class WrapperKlass(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, BudgetPosition):
                return dict(
                    name=obj.name,
                    positions={c: format_decimal(
                        v, c)for c, v in obj.positions.items()},
                    children=obj.children,
                )

            if isinstance(obj, Decimal):
                return f'{obj:.6f}'
            return super().default(obj)
    return WrapperKlass


class BudgetPlan(FavaExtensionBase):
    report_title = 'Budget Plan'
    has_js_module = True

    def budget_plan(self) -> BudgetPosition:
        if g.filtered.date_range is None:
            return []

        root = g.filtered.root_tree

        b, err = budgets.parse_budgets(self.ledger.all_entries_by_type.Custom)
        if err:
            raise ValueError(err)

        acctypes = options.get_account_types(self.ledger.options)

        children: typing.Dict[str, BudgetPosition] = {}

        for acc in root.accounts:
            if not account_types.is_income_statement_account(
                acc, acctypes,
            ):
                continue
            pos = budgets.calculate_budget_children(
                b, acc, g.filtered.date_range.begin, g.filtered.date_range.end,
            )
            if len(pos) == 0:
                continue

            cur = children.setdefault(
                acc.split(':')[0], BudgetPosition('', {}, {}))

            for x in acc.split(':')[1:]:
                cur = cur.children.setdefault(x, BudgetPosition('', {}, {}))
            cur.name = acc
            cur.positions = pos

        positions = {}
        for x in children.values():
            for currency, num in x.positions.items():
                positions[currency] = positions.get(currency, amount.ZERO)-num

        return json.dumps(BudgetPosition(gettext('Net Profit'), positions, children), cls=BudgetPlanEncoder(self.ledger.format_decimal))
