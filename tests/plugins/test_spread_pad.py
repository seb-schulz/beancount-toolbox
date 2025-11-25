import unittest
from datetime import date

from beancount import loader
from beancount.core import amount
from beancount.parser import cmptest

from beancount_toolbox.plugins import spread_pad


class CreatePads(cmptest.TestCase):

    def test_simple_pad(self):
        entries = spread_pad.create_pads(
            date(2022, 1, 1),
            date(2022, 1, 2),
            amount.A('2 EUR'),
            amount.A('1 EUR'),
            meta={},
            account='Assets:Cash',
            source_account='Expenses:Misc',
        )

        self.assertEqual(
            entries[0].narration,
            "(Padding inserted for Balance of 1 EUR for difference -1 EUR [1 / 1])"
        )
        self.assertEqual(entries[0].postings[0].units, amount.A("-1.00 EUR"))

    def test_simple_pad2(self):
        entries = spread_pad.create_pads(
            date(2022, 1, 1),
            date(2022, 1, 2),
            amount.A('3 EUR'),
            amount.A('1 EUR'),
            meta={},
            account='Assets:Cash',
            source_account='Expenses:Misc',
        )

        self.assertEqual(
            entries[0].narration,
            "(Padding inserted for Balance of 1 EUR for difference -2 EUR [1 / 1])"
        )
        self.assertEqual(entries[0].postings[0].units, amount.A("-2 EUR"))

    def test_simple_pad3(self):
        entries = spread_pad.create_pads(
            date(2022, 1, 1),
            date(2022, 1, 3),
            amount.A('3 EUR'),
            amount.A('1 EUR'),
            meta={},
            account='Assets:Cash',
            source_account='Expenses:Misc',
        )

        self.assertEqual(
            entries[0].narration,
            "(Padding inserted for Balance of 1 EUR for difference -1.00 EUR [1 / 2])"
        )
        self.assertEqual(entries[0].postings[0].units, amount.A("-1 EUR"))

        self.assertEqual(
            entries[1].narration,
            "(Padding inserted for Balance of 1 EUR for difference -1.00 EUR [2 / 2])"
        )
        self.assertEqual(entries[1].postings[0].units, amount.A("-1 EUR"))

    def test_simple_pad4(self):
        entries = spread_pad.create_pads(
            date(2022, 1, 1),
            date(2022, 1, 4),
            amount.A('3 EUR'),
            amount.A('1 EUR'),
            meta={},
            account='Assets:Cash',
            source_account='Expenses:Misc',
        )

        self.assertEqual(
            entries[0].narration,
            "(Padding inserted for Balance of 1 EUR for difference -0.67 EUR [1 / 3])"
        )
        self.assertEqual(entries[0].postings[0].units, amount.A("-0.67 EUR"))

        self.assertEqual(
            entries[1].narration,
            "(Padding inserted for Balance of 1 EUR for difference -0.67 EUR [2 / 3])"
        )
        self.assertEqual(entries[1].postings[0].units, amount.A("-0.67 EUR"))

        self.assertEqual(
            entries[2].narration,
            "(Padding inserted for Balance of 1 EUR for difference -0.66 EUR [3 / 3])"
        )
        self.assertEqual(entries[2].postings[0].units, amount.A("-0.66 EUR"))

    def test_simple_pad5(self):
        entries = spread_pad.create_pads(
            date(2022, 1, 1),
            date(2022, 1, 4),
            amount.A('5 EUR'),
            amount.A('2 EUR'),
            meta={},
            account='Assets:Cash',
            source_account='Expenses:Misc',
        )

        self.assertEqual(
            entries[0].narration,
            "(Padding inserted for Balance of 2 EUR for difference -1.00 EUR [1 / 3])"
        )
        self.assertEqual(entries[0].postings[0].units, amount.A("-1.00 EUR"))

        self.assertEqual(
            entries[1].narration,
            "(Padding inserted for Balance of 2 EUR for difference -1.00 EUR [2 / 3])"
        )
        self.assertEqual(entries[1].postings[0].units, amount.A("-1.00 EUR"))

        self.assertEqual(
            entries[2].narration,
            "(Padding inserted for Balance of 2 EUR for difference -1.00 EUR [3 / 3])"
        )
        self.assertEqual(entries[2].postings[0].units, amount.A("-1.00 EUR"))

    def test_simple_pad6(self):
        entries = spread_pad.create_pads(
            date(2022, 1, 1),
            date(2022, 1, 4),
            amount.A('2 EUR'),
            amount.A('5 EUR'),
            meta={},
            account='Assets:Cash',
            source_account='Expenses:Misc',
        )

        self.assertEqual(
            entries[0].narration,
            "(Padding inserted for Balance of 5 EUR for difference 1.00 EUR [1 / 3])"
        )
        self.assertEqual(entries[0].postings[0].units, amount.A("1.00 EUR"))

        self.assertEqual(
            entries[1].narration,
            "(Padding inserted for Balance of 5 EUR for difference 1.00 EUR [2 / 3])"
        )
        self.assertEqual(entries[1].postings[0].units, amount.A("1.00 EUR"))

        self.assertEqual(
            entries[2].narration,
            "(Padding inserted for Balance of 5 EUR for difference 1.00 EUR [3 / 3])"
        )
        self.assertEqual(entries[2].postings[0].units, amount.A("1.00 EUR"))


class SpreadPadOnly(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_spread_one_pad_auto_no_error(self, entires, errors, options_map):
        """
            plugin "beancount_toolbox.plugins.spread_pad"

            2011-01-01 open Assets:Cash
            2011-01-01 open Expenses:Misc

            2011-01-01 * "Something"
              Assets:Cash   -1.00 USD
              Expenses:Misc  1.00 USD

            2011-01-03 custom "pad" Assets:Cash Expenses:Misc

            2011-01-04 balance Assets:Cash 2.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(8, len(entires))
        self.assertEqualEntries(
            r'''
        2011-01-01 open Assets:Cash
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
          Assets:Cash    -1.00 USD
          Expenses:Misc   1.00 USD

        2011-01-01 P "(Padding inserted for Balance of 2.00 USD for difference 1.00 USD [1 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-02 P "(Padding inserted for Balance of 2.00 USD for difference 1.00 USD [2 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-03 custom "pad" Assets:Cash Expenses:Misc

        2011-01-03 P "(Padding inserted for Balance of 2.00 USD for difference 1.00 USD [3 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-04 balance Assets:Cash    2.00 USD
        ''', entires)

    @loader.load_doc(expect_errors=False)
    def test_spread_with_gaps(self, entires, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.spread_pad"

        2011-01-01 open Assets:Cash
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
          Assets:Cash   -1.00 USD
          Expenses:Misc  1.00 USD

        2011-01-04 custom "pad" Assets:Cash Expenses:Misc
          frequency: "2d"

        2011-01-05 balance Assets:Cash 3.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(7, len(entires))
        self.assertEqualEntries(
            r'''
        2011-01-01 open Assets:Cash
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
          Assets:Cash    -1.00 USD
          Expenses:Misc   1.00 USD

        2011-01-02 P "(Padding inserted for Balance of 3.00 USD for difference 2.00 USD [1 / 2])"
          Assets:Cash     2.00 USD
          Expenses:Misc  -2.00 USD

        2011-01-04 P "(Padding inserted for Balance of 3.00 USD for difference 2.00 USD [2 / 2])"
          Assets:Cash     2.00 USD
          Expenses:Misc  -2.00 USD

        2011-01-04 custom "pad" Assets:Cash Expenses:Misc
          frequency: "2d"

        2011-01-05 balance Assets:Cash    3.00 USD
        ''', entires)

    @loader.load_doc(expect_errors=False)
    def test_spread_with_gaps_of_a_week(self, entires, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.spread_pad"

        2011-01-01 open Assets:Cash
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
          Assets:Cash   -1.00 USD
          Expenses:Misc  1.00 USD

        2011-01-07 custom "pad" Assets:Cash Expenses:Misc
          frequency: "1w"

        2011-01-08 balance Assets:Cash 3.00 USD
        """
        self.assertEqual(0, len(errors))
        # self.assertEqual(6, len(entires))
        self.assertEqualEntries(
            r'''
        2011-01-01 open Assets:Cash
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
          Assets:Cash    -1.00 USD
          Expenses:Misc   1.00 USD

        2011-01-07 P "(Padding inserted for Balance of 3.00 USD for difference 4.00 USD [1 / 1])"
          Assets:Cash     4.00 USD
          Expenses:Misc  -4.00 USD

        2011-01-07 custom "pad" Assets:Cash Expenses:Misc
          frequency: "1w"

        2011-01-08 balance Assets:Cash    3.00 USD
        ''', entires)

    @loader.load_doc(expect_errors=False)
    def test_spread_one_pad_auto_no_error2(self, entires, errors, options_map):
        """
            plugin "beancount_toolbox.plugins.spread_pad"

            2011-01-01 open Assets:Cash
            2011-01-01 open Expenses:Misc

            2011-01-01 * "Something"
              Assets:Cash     1.00 USD
              Expenses:Misc  -1.00 USD

            2011-01-03 custom "pad" Assets:Cash Expenses:Misc

            2011-01-04 balance Assets:Cash 4.00 USD

            2011-01-05 custom "pad" Assets:Cash Expenses:Misc

            2011-01-08 balance Assets:Cash 8.00 USD

        """
        self.assertEqual(0, len(errors))
        self.assertEqual(14, len(entires))
        self.assertEqualEntries(
            r'''
        2011-01-01 open Assets:Cash
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-01 P "(Padding inserted for Balance of 4.00 USD for difference 1.00 USD [1 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-02 P "(Padding inserted for Balance of 4.00 USD for difference 1.00 USD [2 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-03 custom "pad" Assets:Cash Expenses:Misc

        2011-01-03 P "(Padding inserted for Balance of 4.00 USD for difference 1.00 USD [3 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-04 balance Assets:Cash    4.00 USD

        2011-01-05 custom "pad" Assets:Cash Expenses:Misc

        2011-01-04 P "(Padding inserted for Balance of 8.00 USD for difference 1.00 USD [1 / 4])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-05 P "(Padding inserted for Balance of 8.00 USD for difference 1.00 USD [2 / 4])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-06 P "(Padding inserted for Balance of 8.00 USD for difference 1.00 USD [3 / 4])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-07 P "(Padding inserted for Balance of 8.00 USD for difference 1.00 USD [4 / 4])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-08 balance Assets:Cash 8.00 USD
        ''', entires)

    @loader.load_doc(expect_errors=False)
    def test_spread_pad_auto_multiple_currency(self, entires, errors,
                                               options_map):
        """
            plugin "beancount_toolbox.plugins.spread_pad"

            2011-01-01 open Assets:Cash
            2011-01-01 open Expenses:Misc

            2011-01-01 * "Something"
              Assets:Cash   1.00 USD
              Expenses:Misc              -1.00 USD

            2011-01-02 * "Something else"
              Assets:Cash   1.00 EUR
              Expenses:Misc              -1.00 EUR

            2011-01-03 custom "pad" Assets:Cash Expenses:Misc

            2011-01-04 balance Assets:Cash 4.00 USD
            2011-01-04 balance Assets:Cash 1.00 EUR

        """
        self.assertEqual(0, len(errors))
        self.assertEqual(10, len(entires))
        self.assertEqualEntries(
            r'''
        2011-01-01 open Assets:Cash
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-01 P "(Padding inserted for Balance of 4.00 USD for difference 1.00 USD [1 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-02 * "Something else"
          Assets:Cash     1.00 EUR
          Expenses:Misc  -1.00 EUR

        2011-01-02 P "(Padding inserted for Balance of 4.00 USD for difference 1.00 USD [2 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-03 custom "pad" Assets:Cash Expenses:Misc

        2011-01-03 P "(Padding inserted for Balance of 4.00 USD for difference 1.00 USD [3 / 3])"
          Assets:Cash     1.00 USD
          Expenses:Misc  -1.00 USD

        2011-01-04 balance Assets:Cash   4.00 USD
        2011-01-04 balance Assets:Cash   1.00 EUR
        ''', entires)

    @loader.load_doc(expect_errors=False)
    def test_spread_pad_regression_v2_to_v3(self, entires, errors,
                                            options_map):
        """
          ; Regression test from production (Beancount v2 to v3 migration)
          ; Production uses: option "plugin_processing_mode" "raw"
          ; with plugin order: pad -> spread_pad -> balance
          ;
          ; This test verifies padding distribution with:
          ; - Consistent base amount for entries 1 through n-1
          ; - Exact remainder in last entry (entry n)
          ; Example: -17.38/6 = -2.90,-2.90,-2.90,-2.90,-2.90,-2.88

          plugin "beancount.plugins.auto_accounts"
          plugin "beancount_toolbox.plugins.spread_pad"

          2021-02-07 open Assets:Cash
          2011-01-01 open Expenses:Misc

          2021-02-07 * "Something"
            Expenses:Misc -93.54 EUR
            Assets:Cash 93.54 EUR

          2021-02-08 balance Assets:Cash  93.54 EUR

          2021-02-08 * "Shop I"
            Assets:Cash -25 EUR
            Expenses:Misc 25 EUR

          2021-02-09 * "Add money"
            Equity:PrivateWithdrawals:A  -100.00 EUR
            Equity:PrivateWithdrawals:B  -100.00 EUR
            Assets:Cash     200.00 EUR

          2021-02-11 custom "pad" Assets:Cash Expenses:Misc -17.38 EUR
          # 2021-02-11 pad Assets:Cash Expenses:Misc

          2021-02-10 * "Expensens"
            Assets:Cash     -55.00 EUR
            Expenses:Misc    55.00 EUR

          2021-02-12 * "Expensens"
            Assets:Cash     -116.95 EUR
            Expenses:Misc    116.95 EUR

          2021-02-13 * "Shop II"
            Assets:Cash -7.39 EUR
            Expenses:Misc 7.39 EUR

          2021-02-13 * "Expensens"
            Assets:Cash     -28.05 EUR
            Expenses:Misc    28.05 EUR

          2021-02-14 balance Assets:Cash  43.77 EUR
          # 2021-02-14 balance Assets:Cash  61.15 EUR
        """
        # self.assertEqual(0, len(errors))
        # self.assertEqual(10, len(entires))
        self.assertEqualEntries(
            r'''
            2021-02-07 open Assets:Cash
            2011-01-01 open Expenses:Misc

            2021-02-09 open Equity:PrivateWithdrawals:A
            2021-02-09 open Equity:PrivateWithdrawals:B

            2021-02-07 * "Something"
              Expenses:Misc -93.54 EUR
              Assets:Cash 93.54 EUR

            2021-02-08 * "Shop I"
              Assets:Cash -25 EUR
              Expenses:Misc 25 EUR

            2021-02-13 * "Shop II"
              Assets:Cash -7.39 EUR
              Expenses:Misc 7.39 EUR

            2021-02-08 balance Assets:Cash  93.54 EUR

            2021-02-08 P "(Padding inserted for Balance of 43.77 EUR for difference -2.90 EUR [1 / 6])"
              Assets:Cash    -2.90 EUR
              Expenses:Misc   2.90 EUR

            2021-02-09 P "(Padding inserted for Balance of 43.77 EUR for difference -2.90 EUR [2 / 6])"
              Assets:Cash    -2.90 EUR
              Expenses:Misc   2.90 EUR

            2021-02-09 * "Add money"
              Equity:PrivateWithdrawals:A  -100.00 EUR
              Equity:PrivateWithdrawals:B  -100.00 EUR
              Assets:Cash     200.00 EUR

            2021-02-10 P "(Padding inserted for Balance of 43.77 EUR for difference -2.90 EUR [3 / 6])"
              Assets:Cash    -2.90 EUR
              Expenses:Misc   2.90 EUR

            2021-02-11 P "(Padding inserted for Balance of 43.77 EUR for difference -2.90 EUR [4 / 6])"
              Assets:Cash    -2.90 EUR
              Expenses:Misc   2.90 EUR

            2021-02-12 P "(Padding inserted for Balance of 43.77 EUR for difference -2.90 EUR [5 / 6])"
              Assets:Cash    -2.90 EUR
              Expenses:Misc   2.90 EUR

            2021-02-13 P "(Padding inserted for Balance of 43.77 EUR for difference -2.88 EUR [6 / 6])"
              Assets:Cash    -2.88 EUR
              Expenses:Misc   2.88 EUR

            2021-02-11 custom "pad" Assets:Cash Expenses:Misc -17.38 EUR

            2021-02-10 * "Expensens"
              Assets:Cash     -55.00 EUR
              Expenses:Misc    55.00 EUR

            # 2021-02-11 pad Assets:Cash Expenses:Misc

            # 2021-02-11 P "(Padding inserted for Balance of 43.77 EUR for difference -17.38 EUR)"
            #   Assets:Cash    -17.38 EUR
            #   Expenses:Misc   17.38 EUR

            2021-02-12 * "Expensens"
              Assets:Cash     -116.95 EUR
              Expenses:Misc    116.95 EUR

            2021-02-13 * "Expensens"
              Assets:Cash     -28.05 EUR
              Expenses:Misc    28.05 EUR

            2021-02-14 balance Assets:Cash  43.77 EUR
            # 2021-02-14 balance Assets:Cash  61.15 EUR
        ''', entires)

    @loader.load_doc(expect_errors=False)
    def test_spread_pad_default_plugin_order_issue(self, entires, errors,
                                                   options_map):
        """
          ; This test demonstrates behavior with DEFAULT plugin order
          ; Without option "plugin_processing_mode" "raw" and explicit
          ; plugin ordering, the spread_pad plugin starts padding from
          ; the SAME day as the balance assertion (not the next day).
          ;
          ; This differs from production which uses:
          ;   option "plugin_processing_mode" "raw"
          ;   plugin "beancount.ops.pad"
          ;   plugin "beancount_toolbox.plugins.spread_pad"
          ;   plugin "beancount.ops.balance"
          ;
          ; With default order, padding starts on 2021-02-08 (balance date)
          ; instead of 2021-02-09 (day after balance).

          plugin "beancount.plugins.auto_accounts"
          plugin "beancount_toolbox.plugins.spread_pad"

          2021-02-06 open Assets:Cash
          2021-02-06 open Expenses:Misc

          2021-02-06 * "Initial"
            Assets:Cash 200.00 EUR
            Expenses:Misc -200.00 EUR

          2021-02-07 pad Assets:Cash Expenses:Misc

          2021-02-08 balance Assets:Cash 100.00 EUR

          2021-02-08 custom "pad" Assets:Cash Expenses:Misc -30.00 EUR

          2021-02-11 balance Assets:Cash 70.00 EUR
        """
        self.assertEqualEntries(
            r'''
            2021-02-06 open Assets:Cash
            2021-02-06 open Expenses:Misc

            2021-02-06 * "Initial"
              Assets:Cash 200.00 EUR
              Expenses:Misc -200.00 EUR

            2021-02-07 pad Assets:Cash Expenses:Misc

            2021-02-07 P "(Padding inserted for Balance of 100.00 EUR for difference -100.00 EUR)"
              Assets:Cash    -100.00 EUR
              Expenses:Misc   100.00 EUR

            2021-02-08 balance Assets:Cash 100.00 EUR

            2021-02-08 P "(Padding inserted for Balance of 70.00 EUR for difference -10.00 EUR [1 / 3])"
              Assets:Cash    -10.00 EUR
              Expenses:Misc   10.00 EUR

            2021-02-09 P "(Padding inserted for Balance of 70.00 EUR for difference -10.00 EUR [2 / 3])"
              Assets:Cash    -10.00 EUR
              Expenses:Misc   10.00 EUR

            2021-02-10 P "(Padding inserted for Balance of 70.00 EUR for difference -10.00 EUR [3 / 3])"
              Assets:Cash    -10.00 EUR
              Expenses:Misc   10.00 EUR

            2021-02-08 custom "pad" Assets:Cash Expenses:Misc -30.00 EUR

            2021-02-11 balance Assets:Cash 70.00 EUR
        ''', entires)

    @loader.load_doc(expect_errors=True)
    def test_spread_pad_explicit_amount_different_from_calculated(self, entires, errors,
                                                                  options_map):
        """
          ; Test that explicit amount in custom pad directive is used
          ; even when it differs from the calculated amount.
          ;
          ; Calculated amount would be: 80.00 - 100.00 = -20.00 EUR
          ; But explicit amount is: -40.00 EUR
          ; The plugin should use -40.00 EUR and spread it across 3 days,
          ; resulting in a balance of 60.00 EUR (100 - 40).
          ; This causes the balance assertion to fail, which is expected.

          plugin "beancount.plugins.auto_accounts"
          plugin "beancount_toolbox.plugins.spread_pad"

          2021-02-06 open Assets:Cash
          2021-02-06 open Expenses:Misc

          2021-02-06 * "Initial"
            Assets:Cash 100.00 EUR
            Expenses:Misc -100.00 EUR

          2021-02-07 balance Assets:Cash 100.00 EUR

          2021-02-08 custom "pad" Assets:Cash Expenses:Misc -40.00 EUR

          2021-02-11 balance Assets:Cash 80.00 EUR
        """
        # Verify that the explicit amount was used (-40.00 EUR spread across 4 days)
        # even though it causes a balance error
        self.assertEqual(1, len(errors))  # Expect balance error
        self.assertRegex(str(errors[0]), "Balance.*80.00 EUR.*60.00 EUR")

        self.assertEqualEntries(
            r'''
            2021-02-06 open Assets:Cash
            2021-02-06 open Expenses:Misc

            2021-02-06 * "Initial"
              Assets:Cash 100.00 EUR
              Expenses:Misc -100.00 EUR

            2021-02-07 balance Assets:Cash 100.00 EUR

            2021-02-07 P "(Padding inserted for Balance of 80.00 EUR for difference -10.00 EUR [1 / 4])"
              Assets:Cash    -10.00 EUR
              Expenses:Misc   10.00 EUR

            2021-02-08 P "(Padding inserted for Balance of 80.00 EUR for difference -10.00 EUR [2 / 4])"
              Assets:Cash    -10.00 EUR
              Expenses:Misc   10.00 EUR

            2021-02-09 P "(Padding inserted for Balance of 80.00 EUR for difference -10.00 EUR [3 / 4])"
              Assets:Cash    -10.00 EUR
              Expenses:Misc   10.00 EUR

            2021-02-10 P "(Padding inserted for Balance of 80.00 EUR for difference -10.00 EUR [4 / 4])"
              Assets:Cash    -10.00 EUR
              Expenses:Misc   10.00 EUR

            2021-02-08 custom "pad" Assets:Cash Expenses:Misc -40.00 EUR

            2021-02-11 balance Assets:Cash 80.00 EUR
        ''', entires)


if __name__ == '__main__':
    unittest.main()
