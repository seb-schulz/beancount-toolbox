"""Tests for portfolio-exclude directive functionality."""
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


class PortfolioMonitorExcludeTest(cmptest.TestCase):
    """Test portfolio-exclude directive behavior."""

    root_account = "Assets:Investments"

    def _run_extension(self, doc: str, time_filter: str | None = None):
        """Helper to run portfolio extension with given beancount doc."""
        bean_data = textwrap.dedent(doc).strip() + "\n"
        with tempfile.NamedTemporaryFile("w", suffix=".bean", delete=False) as handle:
            handle.write(bean_data)
            path = handle.name

        try:
            ledger = FavaLedger(path)
            app = Flask(__name__)
            with app.app_context():
                if time_filter:
                    filtered = ledger.get_filtered(time=time_filter)
                else:
                    filtered = ledger.get_filtered()
                g.ledger = ledger
                g.filtered = filtered
                return portfolio({"root_account": self.root_account}, None)
        finally:
            os.remove(path)

    @loader.load_doc(expect_errors=False)
    def test_exclude_directive_removes_account(self, entries, errors, options_map):
        """
          option "operating_currency" "USD"

          2020-01-01 open Assets:Investments:Stock1 STOCK1
          2020-01-01 open Assets:Investments:Stock2 STOCK2
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.5
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.5

          2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2

          2020-01-01 * "Initial positions"
            Assets:Investments:Stock1        10 STOCK1 {10 USD}
            Assets:Investments:Stock2        10 STOCK2 {10 USD}
            Equity:Opening-Balances              -200 USD
        """
        doc = self.test_exclude_directive_removes_account.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        result = self._run_extension(doc)

        accounts = {row[0] for row in result.table.rows}

        # Stock1 should be present
        assert "Assets:Investments:Stock1" in accounts
        # Stock2 should be excluded
        assert "Assets:Investments:Stock2" not in accounts

    @loader.load_doc(expect_errors=False)
    def test_exclude_directive_date_filtering_includes_past(self, entries, errors, options_map):
        """
          option "operating_currency" "USD"

          2020-01-01 open Assets:Investments:Stock1 STOCK1
          2020-01-01 open Assets:Investments:Stock2 STOCK2
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.5
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.5

          2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2

          2020-01-01 * "Initial positions"
            Assets:Investments:Stock1        10 STOCK1 {10 USD}
            Assets:Investments:Stock2        10 STOCK2 {10 USD}
            Equity:Opening-Balances              -200 USD
        """
        doc = self.test_exclude_directive_date_filtering_includes_past.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        # View portfolio as of 2020-06-01 (after exclude date)
        result = self._run_extension(doc, "2020-01-01 to 2020-06-01")

        accounts = {row[0] for row in result.table.rows}

        # Stock2 excluded on 2020-01-01 should still be excluded when viewing 2020-06-01
        assert "Assets:Investments:Stock1" in accounts
        assert "Assets:Investments:Stock2" not in accounts

    @loader.load_doc(expect_errors=False)
    def test_exclude_directive_date_filtering_excludes_future(self, entries, errors, options_map):
        """

          option "operating_currency" "USD"
          option "name_assets" "Assets"

          2020-01-01 open Assets:Investments:Stock1 STOCK1
          2020-01-01 open Assets:Investments:Stock2 STOCK2
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.5
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.5

          2020-06-01 custom "portfolio-exclude" Assets:Investments:Stock2

          2020-01-01 * "Initial positions"
            Assets:Investments:Stock1        10 STOCK1 {10 USD}
            Assets:Investments:Stock2        10 STOCK2 {10 USD}
            Equity:Opening-Balances              -200 USD
        """
        doc = self.test_exclude_directive_date_filtering_excludes_future.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        # View portfolio as of 2020-03-01 (before exclude date)
        result = self._run_extension(doc, "2020-01-01 to 2020-03-01")

        accounts = {row[0] for row in result.table.rows}

        # Stock2 excluded on 2020-06-01 should STILL BE VISIBLE when viewing 2020-03-01
        assert "Assets:Investments:Stock1" in accounts
        assert "Assets:Investments:Stock2" in accounts

    @loader.load_doc(expect_errors=False)
    def test_exclude_directive_on_date_boundary(self, entries, errors, options_map):
        """

          option "operating_currency" "USD"
          option "name_assets" "Assets"

          2020-01-01 open Assets:Investments:Stock1 STOCK1
          2020-01-01 open Assets:Investments:Stock2 STOCK2
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.5
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.5

          2020-03-01 custom "portfolio-exclude" Assets:Investments:Stock2

          2020-01-01 * "Initial positions"
            Assets:Investments:Stock1        10 STOCK1 {10 USD}
            Assets:Investments:Stock2        10 STOCK2 {10 USD}
            Equity:Opening-Balances              -200 USD
        """
        doc = self.test_exclude_directive_on_date_boundary.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        # View portfolio exactly on exclude date
        result = self._run_extension(doc, "2020-01-01 to 2020-03-01")

        accounts = {row[0] for row in result.table.rows}

        # Directive dated 2020-03-01 SHOULD apply when viewing up to 2020-03-01 (inclusive)
        assert "Assets:Investments:Stock1" in accounts
        assert "Assets:Investments:Stock2" not in accounts

    @loader.load_doc(expect_errors=False)
    def test_multiple_exclude_directives(self, entries, errors, options_map):
        """

          option "operating_currency" "USD"
          option "name_assets" "Assets"

          2020-01-01 open Assets:Investments:Stock1 STOCK1
          2020-01-01 open Assets:Investments:Stock2 STOCK2
          2020-01-01 open Assets:Investments:Stock3 STOCK3
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.33
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.33
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.34

          2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2
          2020-02-01 custom "portfolio-exclude" Assets:Investments:Stock3

          2020-01-01 * "Initial positions"
            Assets:Investments:Stock1        10 STOCK1 {10 USD}
            Assets:Investments:Stock2        10 STOCK2 {10 USD}
            Assets:Investments:Stock3        10 STOCK3 {10 USD}
            Equity:Opening-Balances              -300 USD
        """
        doc = self.test_multiple_exclude_directives.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        result = self._run_extension(doc, "2020-01-01 to 2020-06-01")

        accounts = {row[0] for row in result.table.rows}

        assert "Assets:Investments:Stock1" in accounts
        assert "Assets:Investments:Stock2" not in accounts
        assert "Assets:Investments:Stock3" not in accounts

    @loader.load_doc(expect_errors=False)
    def test_exclude_and_close_both_work(self, entries, errors, options_map):
        """

          option "operating_currency" "USD"
          option "name_assets" "Assets"

          2020-01-01 open Assets:Investments:Stock1 STOCK1
          2020-01-01 open Assets:Investments:Stock2 STOCK2
          2020-01-01 open Assets:Investments:Stock3 STOCK3
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.33
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.33
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.34

          2020-01-15 close Assets:Investments:Stock2
          2020-01-15 custom "portfolio-exclude" Assets:Investments:Stock3

          2020-01-01 * "Initial positions"
            Assets:Investments:Stock1        10 STOCK1 {10 USD}
            Assets:Investments:Stock2        10 STOCK2 {10 USD}
            Assets:Investments:Stock3        10 STOCK3 {10 USD}
            Equity:Opening-Balances              -300 USD
        """
        doc = self.test_exclude_and_close_both_work.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        result = self._run_extension(doc)

        accounts = {row[0] for row in result.table.rows}

        # Only Stock1 should remain
        assert "Assets:Investments:Stock1" in accounts
        assert "Assets:Investments:Stock2" not in accounts  # closed
        assert "Assets:Investments:Stock3" not in accounts  # excluded

    @loader.load_doc(expect_errors=False)
    def test_duplicate_exclude_same_account(self, entries, errors, options_map):
        """

          option "operating_currency" "USD"
          option "name_assets" "Assets"

          2020-01-01 open Assets:Investments:Stock1 STOCK1
          2020-01-01 open Assets:Investments:Stock2 STOCK2
          2020-01-01 open Equity:Opening-Balances USD

          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.5
          2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.5

          2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2
          2020-02-01 custom "portfolio-exclude" Assets:Investments:Stock2

          2020-01-01 * "Initial positions"
            Assets:Investments:Stock1        10 STOCK1 {10 USD}
            Assets:Investments:Stock2        10 STOCK2 {10 USD}
            Equity:Opening-Balances              -200 USD
        """
        doc = self.test_duplicate_exclude_same_account.__func__.__input__  # pyright: ignore[reportFunctionMemberAccess]
        result = self._run_extension(doc)

        accounts = {row[0] for row in result.table.rows}

        # Should handle duplicates gracefully (frozenset deduplicates)
        assert "Assets:Investments:Stock1" in accounts
        assert "Assets:Investments:Stock2" not in accounts
