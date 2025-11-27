from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from tests.ext._portfolio_test_helpers import load_portfolio


class PortfolioMonitorPriceTest(unittest.TestCase):
    root_account = "Assets:Investments:Stock"

    @load_portfolio(time_filter="2020-01-01 to 2020-01-03")
    def test_last_price_value_matches_selected_period(self, result):
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
        rows_by_account = {row[0]: row for row in result.table.rows}
        stock_row = rows_by_account[self.root_account]

        self.assertEqual(stock_row[-1], date(2020, 1, 2))
        price_inventory = stock_row[3]
        self.assertIsNotNone(price_inventory)
        self.assertEqual(price_inventory.get("USD"), Decimal("12"))

    @load_portfolio(time_filter="2020-01-01 to 2020-01-10")
    def test_last_price_value_updates_with_longer_period(self, result):
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
        rows_by_account = {row[0]: row for row in result.table.rows}
        stock_row = rows_by_account[self.root_account]

        self.assertEqual(stock_row[-1], date(2020, 1, 5))
        price_inventory = stock_row[3]
        self.assertIsNotNone(price_inventory)
        self.assertEqual(price_inventory.get("USD"), Decimal("20"))
