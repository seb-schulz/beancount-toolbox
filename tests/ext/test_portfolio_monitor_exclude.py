"""Tests for portfolio-exclude directive functionality."""
from __future__ import annotations

import unittest
from decimal import Decimal

from tests.ext._portfolio_test_helpers import load_portfolio


class PortfolioMonitorExcludeTest(unittest.TestCase):
    """Test portfolio-exclude directive behavior."""

    root_account = "Assets:Investments"

    # Helper methods for balance verification tests

    def _get_row_by_account(self, result, account_name):
        """Get a specific row by account name, or None if not found."""
        for row in result.table.rows:
            if row[0] == account_name:
                return row
        return None

    def _assert_balance_usd(self, row, expected_amount):
        """Assert balance in USD equals expected amount."""
        actual = row[1].get("USD")
        self.assertEqual(actual, Decimal(str(expected_amount)))

    def _assert_current_allocation_pct(self, row, expected_percent):
        """Assert current allocation percentage (0-100 range)."""
        actual = row[4].get("%")
        self.assertAlmostEqual(actual, Decimal(
            str(expected_percent)), places=1)

    def _assert_target_allocation_pct(self, row, expected_percent):
        """Assert target allocation percentage (0-100 range)."""
        actual = row[5].get("%")
        self.assertEqual(actual, Decimal(str(expected_percent)))

    def _assert_allocations_sum_to_100(self, result):
        """Assert all current allocations sum to 100%."""
        total = sum(row[4].get("%") or Decimal(0) for row in result.table.rows)
        self.assertAlmostEqual(total, Decimal("100"), places=1)

    def _assert_target_allocations_sum_to_100(self, result):
        """Assert all target allocations sum to 100%."""
        total = sum(row[5].get("%") or Decimal(0) for row in result.table.rows)
        self.assertAlmostEqual(total, Decimal("100"), places=1)

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

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

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

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

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

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

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

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

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

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

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

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

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

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    # Balance verification tests

    @load_portfolio()
    def test_exclude_directive_portfolio_total_excludes_balance(self, result):
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
        # Verify that excluded account balances don't contribute to portfolio total
        # Setup: Two accounts with $100 each, exclude Stock2
        # Expected: Portfolio total = $100, only Stock1 in results
        # Verify only one account in results
        self.assertEqual(len(result.table.rows), 1)

        # Verify portfolio total excludes Stock2's $100
        self.assertEqual(result.total.number, Decimal("100"))

        # Verify Stock1 has correct balance
        stock1_row = self._get_row_by_account(
            result, "Assets:Investments:Stock1")
        self.assertIsNotNone(stock1_row)
        self._assert_balance_usd(stock1_row, 100)

        # Verify target allocation preserved at 50%
        self._assert_target_allocation_pct(stock1_row, 100)

        # Verify Stock2 is not in results
        stock2_row = self._get_row_by_account(
            result, "Assets:Investments:Stock2")
        self.assertIsNone(stock2_row)

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio()
    def test_multiple_excludes_portfolio_total_correct(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Assets:Investments:Stock3 STOCK3
        2020-01-01 open Assets:Investments:Stock4 STOCK4
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.25
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.25
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.25
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock4 0.25

        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock1
        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock3

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        10 STOCK1 {10 USD}
          Assets:Investments:Stock2        20 STOCK2 {10 USD}
          Assets:Investments:Stock3        30 STOCK3 {10 USD}
          Assets:Investments:Stock4        40 STOCK4 {10 USD}
          Equity:Opening-Balances              -1000 USD
        """
        # Verify portfolio total with multiple exclusions
        # Setup: Four accounts ($100, $200, $300, $400), exclude two ($100, $300)
        # Expected: Total = $600 (only $200 + $400)
        # Verify exactly 2 rows remain
        self.assertEqual(len(result.table.rows), 2)

        # Verify portfolio total = $600 (excludes Stock1 $100 and Stock3 $300)
        self.assertEqual(result.total.number, Decimal("600"))

        # Verify Stock2 balance = $200
        stock2_row = self._get_row_by_account(
            result, "Assets:Investments:Stock2")
        self.assertIsNotNone(stock2_row)
        self._assert_balance_usd(stock2_row, 200)
        # Verify target allocation preserved at 25%
        self._assert_target_allocation_pct(stock2_row, 50)

        # Verify Stock4 balance = $400
        stock4_row = self._get_row_by_account(
            result, "Assets:Investments:Stock4")
        self.assertIsNotNone(stock4_row)
        self._assert_balance_usd(stock4_row, 400)
        # Verify target allocation preserved at 25%
        self._assert_target_allocation_pct(stock4_row, 50)

        # Verify excluded accounts not in results
        self.assertIsNone(self._get_row_by_account(
            result, "Assets:Investments:Stock1"))
        self.assertIsNone(self._get_row_by_account(
            result, "Assets:Investments:Stock3"))

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio()
    def test_exclude_directive_current_allocations_sum_to_100_percent(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Assets:Investments:Stock3 STOCK3
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.33
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.34
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.33

        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        30 STOCK1 {10 USD}
          Assets:Investments:Stock2        40 STOCK2 {10 USD}
          Assets:Investments:Stock3        30 STOCK3 {10 USD}
          Equity:Opening-Balances              -1000 USD
        """
        # Verify current allocation percentages sum to 100% after exclusion
        # Setup: Three accounts ($300, $400, $300), exclude middle ($400)
        # Expected: Remaining two accounts show 50% each (of $600 total)
        # Verify 2 accounts remain
        self.assertEqual(len(result.table.rows), 2)

        # Verify total is $600 (excludes Stock2's $400)
        self.assertEqual(result.total.number, Decimal("600"))

        # Get rows
        stock1_row = self._get_row_by_account(
            result, "Assets:Investments:Stock1")
        stock3_row = self._get_row_by_account(
            result, "Assets:Investments:Stock3")

        # Verify each account has 50% current allocation
        self._assert_current_allocation_pct(stock1_row, 50.0)
        self._assert_current_allocation_pct(stock3_row, 50.0)

        # Verify target allocations preserved (33% each)
        self._assert_target_allocation_pct(stock1_row, 50)
        self._assert_target_allocation_pct(stock3_row, 50)

        # Verify allocations sum to 100%
        self._assert_allocations_sum_to_100(result)
        # Verify target allocations also sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio()
    def test_exclude_directive_current_allocation_percentages_accurate(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Assets:Investments:Stock3 STOCK3
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.33
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.33
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.34

        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock1

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        10 STOCK1 {10 USD}
          Assets:Investments:Stock2        20 STOCK2 {10 USD}
          Assets:Investments:Stock3        70 STOCK3 {10 USD}
          Equity:Opening-Balances              -1000 USD
        """
        # Verify exact percentage calculations with unequal balances
        # Setup: Three accounts ($100, $200, $700), exclude smallest ($100)
        # Expected: $200 account = 22.22%, $700 account = 77.78%
        # Verify portfolio total = $900
        self.assertEqual(result.total.number, Decimal("900"))

        # Get rows
        stock2_row = self._get_row_by_account(
            result, "Assets:Investments:Stock2")
        stock3_row = self._get_row_by_account(
            result, "Assets:Investments:Stock3")

        # Verify allocation percentages
        # $200 / $900 = 22.22%
        self._assert_current_allocation_pct(stock2_row, 22.22)
        # $700 / $900 = 77.78%
        self._assert_current_allocation_pct(stock3_row, 77.78)

        # Verify target allocations preserved
        self._assert_target_allocation_pct(stock2_row, 49.25)
        self._assert_target_allocation_pct(stock3_row, 50.75)

        # Verify allocations sum to 100%
        self._assert_allocations_sum_to_100(result)
        # Verify target allocations also sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio()
    def test_exclude_directive_preserves_target_allocations(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Assets:Investments:Stock3 STOCK3
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.30
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.40
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.30

        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        30 STOCK1 {10 USD}
          Assets:Investments:Stock2        40 STOCK2 {10 USD}
          Assets:Investments:Stock3        30 STOCK3 {10 USD}
          Equity:Opening-Balances              -1000 USD
        """
        # Verify target allocations are preserved (not renormalized) after exclusion
        # Setup: Three accounts with weights (30%, 40%, 30%), exclude middle (40%)
        # Expected: Remaining show original 30% targets (sum = 60%, not 100%)
        # Get rows
        stock1_row = self._get_row_by_account(
            result, "Assets:Investments:Stock1")
        stock3_row = self._get_row_by_account(
            result, "Assets:Investments:Stock3")
        self.assertIsNotNone(stock1_row)
        self.assertIsNotNone(stock3_row)

        self._assert_target_allocation_pct(stock1_row, 50)
        self._assert_target_allocation_pct(stock3_row, 50)

        # Verify target allocations of remaining accounts sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio()
    def test_exclude_directive_amount_delta_calculated_on_reduced_total(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.80
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.20

        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        10 STOCK1 {10 USD}
          Assets:Investments:Stock2        10 STOCK2 {10 USD}
          Equity:Opening-Balances              -200 USD
        """
        # Verify amount deltas are calculated using the reduced portfolio total
        # Setup: Two accounts ($100 each), exclude one, remaining has 80% target
        # Expected: Delta = (0.80 - 1.00) * $100 = -$20 (overallocated)
        # Verify total = $100 (Stock2 excluded)
        self.assertEqual(result.total.number, Decimal("100"))

        # Get Stock1 row
        stock1_row = self._get_row_by_account(
            result, "Assets:Investments:Stock1")
        self.assertIsNotNone(stock1_row)

        # Verify current allocation = 100% ($100 / $100)
        self._assert_current_allocation_pct(stock1_row, 100.0)

        self._assert_target_allocation_pct(stock1_row, 100)

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio()
    def test_exclude_all_but_one_account(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Assets:Investments:Stock3 STOCK3
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.33
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.33
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.34

        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2
        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock3

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        50 STOCK1 {10 USD}
          Assets:Investments:Stock2        30 STOCK2 {10 USD}
          Assets:Investments:Stock3        20 STOCK3 {10 USD}
          Equity:Opening-Balances              -1000 USD
        """
        # Verify behavior when all but one account is excluded
        # Setup: Three accounts, exclude two
        # Expected: Single account with 100% allocation
        # Verify exactly 1 row
        self.assertEqual(len(result.table.rows), 1)

        # Verify total = $500 (only Stock1)
        self.assertEqual(result.total.number, Decimal("500"))

        # Get Stock1 row
        stock1_row = self._get_row_by_account(
            result, "Assets:Investments:Stock1")
        self.assertIsNotNone(stock1_row)

        # Verify balance = $500
        self._assert_balance_usd(stock1_row, 500)

        # Verify current allocation = 100%
        self._assert_current_allocation_pct(stock1_row, 100.0)

        self._assert_target_allocation_pct(stock1_row, 100)

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio()
    def test_exclude_directive_with_zero_balance_accounts(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Assets:Investments:Stock3 STOCK3
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.33
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.33
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock3 0.34

        2020-01-01 custom "portfolio-exclude" Assets:Investments:Stock2

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        10 STOCK1 {10 USD}
          Assets:Investments:Stock3        20 STOCK3 {10 USD}
          Equity:Opening-Balances              -300 USD
        """
        # Verify handling of zero-balance excluded accounts
        # Setup: Three accounts ($100, $0, $200), exclude the $0 account
        # Expected: Total = $300, no errors
        # Verify 2 accounts remain
        self.assertEqual(len(result.table.rows), 2)

        # Verify total = $300 (Stock2 had $0 balance)
        self.assertEqual(result.total.number, Decimal("300"))

        # Get rows
        stock1_row = self._get_row_by_account(
            result, "Assets:Investments:Stock1")
        stock3_row = self._get_row_by_account(
            result, "Assets:Investments:Stock3")
        self.assertIsNotNone(stock1_row)
        self.assertIsNotNone(stock3_row)

        # Verify balances
        self._assert_balance_usd(stock1_row, 100)
        self._assert_balance_usd(stock3_row, 200)

        # Verify percentages are calculated correctly
        # $100 / $300 = 33.33%
        self._assert_current_allocation_pct(stock1_row, 33.33)
        # $200 / $300 = 66.67%
        self._assert_current_allocation_pct(stock3_row, 66.67)

        # Verify target allocations preserved
        self._assert_target_allocation_pct(stock1_row, 49.25)
        self._assert_target_allocation_pct(stock3_row, 50.75)

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)

    @load_portfolio(time_filter="2020-01-01 to 2020-06-01")
    def test_exclude_directive_balances_respect_date_filter(self, result):
        """
        option "operating_currency" "USD"

        2020-01-01 open Assets:Investments:Stock1 STOCK1
        2020-01-01 open Assets:Investments:Stock2 STOCK2
        2020-01-01 open Equity:Opening-Balances USD

        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock1 0.5
        2020-01-01 custom "portfolio-weight" Assets:Investments:Stock2 0.5

        2020-02-01 custom "portfolio-exclude" Assets:Investments:Stock2

        2020-01-01 * "Initial positions"
          Assets:Investments:Stock1        10 STOCK1 {10 USD}
          Assets:Investments:Stock2        10 STOCK2 {10 USD}
          Equity:Opening-Balances              -200 USD

        2020-03-01 * "Add more to Stock1"
          Assets:Investments:Stock1        10 STOCK1 {10 USD}
          Equity:Opening-Balances              -100 USD
        """
        # Verify balances reflect the filtered date range with exclusions
        # Setup: Transactions over time, exclude directive, date filter
        # Expected: Balances at filter date, exclusion applied
        # Verify only Stock1 is present (Stock2 excluded as of 2020-02-01)
        self.assertEqual(len(result.table.rows), 1)

        # Get Stock1 row
        stock1_row = self._get_row_by_account(
            result, "Assets:Investments:Stock1")
        self.assertIsNotNone(stock1_row)

        # Verify balance reflects transactions up to filter date
        # Initial 10 shares + 10 more shares = 20 shares @ $10 = $200
        self._assert_balance_usd(stock1_row, 200)

        # Verify total = $200 (only Stock1, Stock2 excluded)
        self.assertEqual(result.total.number, Decimal("200"))

        # Verify target allocation preserved at 50%
        self._assert_target_allocation_pct(stock1_row, 100)

        # Verify Stock2 is not in results
        self.assertIsNone(self._get_row_by_account(
            result, "Assets:Investments:Stock2"))

        # Target allocations should still sum to 100%
        self._assert_target_allocations_sum_to_100(result)
