"""Tests for portfolio-exclude directive functionality."""
from __future__ import annotations

import unittest

from tests.ext._portfolio_test_helpers import load_portfolio


class PortfolioMonitorExcludeTest(unittest.TestCase):
    """Test portfolio-exclude directive behavior."""

    root_account = "Assets:Investments"

    @load_portfolio()
    def test_exclude_directive_removes_account(self, result):
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
        accounts = {row[0] for row in result.table.rows}

        # Stock1 should be present
        self.assertIn("Assets:Investments:Stock1", accounts)
        # Stock2 should be excluded
        self.assertNotIn("Assets:Investments:Stock2", accounts)

    @load_portfolio(time_filter="2020-01-01 to 2020-06-01")
    def test_exclude_directive_date_filtering_includes_past(self, result):
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
        accounts = {row[0] for row in result.table.rows}

        # Stock2 excluded on 2020-01-01 should still be excluded when viewing 2020-06-01
        self.assertIn("Assets:Investments:Stock1", accounts)
        self.assertNotIn("Assets:Investments:Stock2", accounts)

    @load_portfolio(time_filter="2020-01-01 to 2020-03-01")
    def test_exclude_directive_date_filtering_excludes_future(self, result):
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
        accounts = {row[0] for row in result.table.rows}

        # Stock2 excluded on 2020-06-01 should STILL BE VISIBLE when viewing 2020-03-01
        self.assertIn("Assets:Investments:Stock1", accounts)
        self.assertIn("Assets:Investments:Stock2", accounts)

    @load_portfolio(time_filter="2020-01-01 to 2020-03-01")
    def test_exclude_directive_on_date_boundary(self, result):
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
        accounts = {row[0] for row in result.table.rows}

        # Directive dated 2020-03-01 SHOULD apply when viewing up to 2020-03-01 (inclusive)
        self.assertIn("Assets:Investments:Stock1", accounts)
        self.assertNotIn("Assets:Investments:Stock2", accounts)

    @load_portfolio(time_filter="2020-01-01 to 2020-06-01")
    def test_multiple_exclude_directives(self, result):
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
        accounts = {row[0] for row in result.table.rows}

        self.assertIn("Assets:Investments:Stock1", accounts)
        self.assertNotIn("Assets:Investments:Stock2", accounts)
        self.assertNotIn("Assets:Investments:Stock3", accounts)

    @load_portfolio()
    def test_exclude_and_close_both_work(self, result):
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
        accounts = {row[0] for row in result.table.rows}

        # Only Stock1 should remain
        self.assertIn("Assets:Investments:Stock1", accounts)
        self.assertNotIn("Assets:Investments:Stock2", accounts)  # closed
        self.assertNotIn("Assets:Investments:Stock3", accounts)  # excluded

    @load_portfolio()
    def test_duplicate_exclude_same_account(self, result):
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
        accounts = {row[0] for row in result.table.rows}

        # Should handle duplicates gracefully (frozenset deduplicates)
        self.assertIn("Assets:Investments:Stock1", accounts)
        self.assertNotIn("Assets:Investments:Stock2", accounts)
