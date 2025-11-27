from __future__ import annotations

import os
import tempfile
import textwrap
from datetime import date
from decimal import Decimal

from beancount import loader
from beancount.parser import cmptest
from fava.context import g
from fava.core import FavaLedger
from flask import Flask

from beancount_toolbox.ext.portfolio_monitor import portfolio


class PortfolioMonitorPriceTest(cmptest.TestCase):
    root_account = "Assets:Investments:Stock"

    def _run_extension(self, doc: str, time_filter: str):
        bean_data = textwrap.dedent(doc).strip() + "\n"
        with tempfile.NamedTemporaryFile("w", suffix=".bean", delete=False) as handle:
            handle.write(bean_data)
            path = handle.name

        try:
            ledger = FavaLedger(path)
            app = Flask(__name__)
            with app.app_context():
                filtered = ledger.get_filtered(time=time_filter)
                g.ledger = ledger
                g.filtered = filtered
                return portfolio({"root_account": self.root_account}, None)
        finally:
            os.remove(path)

    @loader.load_doc(expect_errors=False)
    def test_last_price_value_matches_selected_period(self, entries, errors, options_map):
        """
          option "operating_currency" "USD"
          option "name_assets" "Assets"

          2020-01-01 open Assets:Investments:Stock STOCK
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-02 price STOCK 12 USD
          2020-01-05 price STOCK 20 USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock 0.5

          2020-01-01 * "Initial position"
            Assets:Investments:Stock        10 STOCK {12 USD}
            Equity:Opening-Balances              -120 USD
        """
        doc = self.test_last_price_value_matches_selected_period.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        result = self._run_extension(doc, "2020-01-01 to 2020-01-03")

        rows_by_account = {row[0]: row for row in result.table.rows}
        stock_row = rows_by_account[self.root_account]

        assert stock_row[-1] == date(2020, 1, 2)
        price_inventory = stock_row[3]
        assert price_inventory is not None
        assert price_inventory.get("USD") == Decimal("12")

    @loader.load_doc(expect_errors=False)
    def test_last_price_value_updates_with_longer_period(self, entries, errors, options_map):
        """
          option "operating_currency" "USD"
          option "name_assets" "Assets"

          2020-01-01 open Assets:Investments:Stock STOCK
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-02 price STOCK 12 USD
          2020-01-05 price STOCK 20 USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock 0.5

          2020-01-01 * "Initial position"
            Assets:Investments:Stock        10 STOCK {12 USD}
            Equity:Opening-Balances              -120 USD
        """
        doc = self.test_last_price_value_updates_with_longer_period.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        result = self._run_extension(doc, "2020-01-01 to 2020-01-10")

        rows_by_account = {row[0]: row for row in result.table.rows}
        stock_row = rows_by_account[self.root_account]

        assert stock_row[-1] == date(2020, 1, 5)
        price_inventory = stock_row[3]
        assert price_inventory is not None
        assert price_inventory.get("USD") == Decimal("20")
