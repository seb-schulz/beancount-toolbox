import unittest

from beancount import loader
from beancount.parser import cmptest
from beancount.core import amount
from beancount_toolbox.plugins import spread_pad
from datetime import date


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
            "(Padding inserted for Balance of 1 EUR for difference -1.00 EUR [1 / 1])"
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
            "(Padding inserted for Balance of 1 EUR for difference -2.00 EUR [1 / 1])"
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
            "(Padding inserted for Balance of 1 EUR for difference -0.66 EUR [2 / 3])"
        )
        self.assertEqual(entries[1].postings[0].units, amount.A("-0.66 EUR"))

        self.assertEqual(
            entries[2].narration,
            "(Padding inserted for Balance of 1 EUR for difference -0.67 EUR [3 / 3])"
        )
        self.assertEqual(entries[2].postings[0].units, amount.A("-0.67 EUR"))

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


if __name__ == '__main__':
    unittest.main()
