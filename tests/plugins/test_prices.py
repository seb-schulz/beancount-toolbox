import datetime
from beancount import loader

from beancount.parser import cmptest
from beancount.core import data
from beancount_toolbox.plugins import prices
from tests import _helper


class TestPrices(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_plugin_without_fatals(self, _, errors, __):
        """
        plugin "beancount_toolbox.plugins.prices"
        plugin "beancount.plugins.auto_accounts"

        2011-05-17 * "Something"
            Expenses:Food:Restaurant   1.00 USD
            Assets:Other              -1.00 USD
        """
        self.assertEqual(0, len(errors))

    @loader.load_doc(expect_errors=False)
    def test_commodity_btc(self, entries, _errors, options_map):
        """
        option "operating_currency" "EUR"
        plugin "beancount.plugins.auto_accounts"
        2024-09-13 commodity BTC
        """
        self.assertListEqual(
            options_map.get('operating_currency', []),
            ['EUR'],
        )

        got_entries, got_errors = prices.prices(
            entries,
            options_map,
            _helper.fixture_path('prices', 'valid'),
        )

        self.assertEqual(0, len(got_errors))
        self.assertEqualEntries(
            '''
            2024-09-13 commodity BTC

            2024-09-15 price BTC    53354.50 EUR
            2024-09-22 price BTC    56782.42 EUR
            ''', got_entries)

        self.assertEqual(got_entries[-1].meta.get('open', ''), '53354.50 EUR')
        self.assertEqual(got_entries[-1].meta.get('high', ''), '57383.43 EUR')
        self.assertEqual(got_entries[-1].meta.get('low', ''), '51683.41 EUR')
        self.assertEqual(got_entries[-1].meta.get('volume', ''),
                         data.D('8797329548'))

    @loader.load_doc(expect_errors=False)
    def test_commodity_abc(self, entries, _errors, options_map):
        """
        option "operating_currency" "EUR"
        plugin "beancount.plugins.auto_accounts"
        2024-08-14 commodity A.B.C
        """
        self.assertListEqual(
            options_map.get('operating_currency', []),
            ['EUR'],
        )

        got_entries, got_errors = prices.prices(
            entries,
            options_map,
            _helper.fixture_path('prices', 'valid'),
        )

        self.assertEqual(0, len(got_errors))
        self.assertEqualEntries(
            '''
            2024-08-14 commodity A.B.C

            2024-08-16 price A.B.C  66.100 EUR
            2024-08-23 price A.B.C  65.800 EUR
            ''', got_entries)

        self.assertEqual(got_entries[-1].meta.get('open', ''), '66.000 EUR')
        self.assertEqual(got_entries[-1].meta.get('high', ''), '66.400 EUR')
        self.assertEqual(got_entries[-1].meta.get('low', ''), '65.200 EUR')
        self.assertEqual(got_entries[-1].meta.get('volume', ''),
                         data.D('7754'))

    @loader.load_doc(expect_errors=False)
    def test_non_existing_commodity(self, entries, _errors, options_map):
        """
        option "operating_currency" "EUR"
        plugin "beancount.plugins.auto_accounts"
        2009-01-01 commodity XYZ
        """
        self.assertListEqual(
            options_map.get('operating_currency', []),
            ['EUR'],
        )

        got_entries, got_errors = prices.prices(
            entries,
            options_map,
            _helper.fixture_path('prices', 'valid'),
        )

        self.assertEqual(0, len(got_errors))
        self.assertEqualEntries(
            '''
            2009-01-01 commodity XYZ
            ''', got_entries)

    @loader.load_doc(expect_errors=False)
    def test_invalid_file(self, entries, _errors, options_map):
        """
        option "operating_currency" "EUR"
        plugin "beancount.plugins.auto_accounts"
        2024-09-12 commodity BTC
        """
        self.assertListEqual(
            options_map.get('operating_currency', []),
            ['EUR'],
        )

        got_entries, got_errors = prices.prices(
            entries,
            options_map,
            _helper.fixture_path('prices', 'invalid'),
        )

        # self.assertEqual(2, len(got_errors))
        self.assertSequenceEqual(
            [2, 4, 5],
            [x.source['lineno'] for x in got_errors],
        )

        self.assertEqualEntries(
            '''
            2024-09-12 commodity BTC
            2024-09-14 price BTC    54149.93 USD
            ''', got_entries)


class TestDateRangeAndGrouping(cmptest.TestCase):

    def test_date_range(self):
        self.assertListEqual(
            [],
            prices._date_range(
                data.Price({}, datetime.date(2024, 1, 1), None, None),
                data.Price({}, datetime.date(2024, 1, 2), None, None),
            ),
        )
        self.assertListEqual(
            [datetime.date(2024, 1, 7)],
            prices._date_range(
                data.Price({}, datetime.date(2024, 1, 1), None, None),
                data.Price({}, datetime.date(2024, 1, 7), None, None),
            ),
        )
        self.assertListEqual(
            [
                datetime.date(2024, 1, 7),
                datetime.date(2024, 1, 14),
                datetime.date(2024, 1, 21),
                datetime.date(2024, 1, 28),
                datetime.date(2024, 1, 31),
            ],
            prices._date_range(
                data.Price({}, datetime.date(2024, 1, 1), None, None),
                data.Price({}, datetime.date(2024, 2, 1), None, None),
            ),
        )
        self.assertListEqual(
            [
                datetime.date(2024, 2, 4),
                datetime.date(2024, 2, 11),
                datetime.date(2024, 2, 18),
                datetime.date(2024, 2, 25),
                datetime.date(2024, 2, 29),
            ],
            prices._date_range(
                data.Price({}, datetime.date(2024, 2, 1), None, None),
                data.Price({}, datetime.date(2024, 3, 1), None, None),
            ),
        )

    def test_grouping_empty_list_and_range(self):
        self.assertEqual({}, prices._groupby_date([], []))

    def test_grouping(self):
        P = lambda d: data.Price(data.new_metadata('<empty>', 0), d, None, None
                                 )
        got = prices._groupby_date(
            [
                P(datetime.date(2024, 1, 1)),
                P(datetime.date(2024, 1, 2)),
                P(datetime.date(2024, 1, 3)),
                P(datetime.date(2024, 1, 4)),
                P(datetime.date(2024, 1, 5)),
                P(datetime.date(2024, 1, 6)),
                P(datetime.date(2024, 1, 7)),
                P(datetime.date(2024, 1, 8)),
                P(datetime.date(2024, 1, 9)),
                P(datetime.date(2024, 1, 10)),
            ],
            [
                datetime.date(2024, 1, 2),
                datetime.date(2024, 1, 4),
                datetime.date(2024, 1, 9)
            ],
        )
        self.assertDictEqual(
            {
                datetime.date(2024, 1, 2):
                [P(datetime.date(2024, 1, 1)),
                 P(datetime.date(2024, 1, 2))],
                datetime.date(2024, 1, 4):
                [P(datetime.date(2024, 1, 3)),
                 P(datetime.date(2024, 1, 4))],
                datetime.date(2024, 1, 9): [
                    P(datetime.date(2024, 1, 5)),
                    P(datetime.date(2024, 1, 6)),
                    P(datetime.date(2024, 1, 7)),
                    P(datetime.date(2024, 1, 8)),
                    P(datetime.date(2024, 1, 9))
                ],
            },
            got,
        )

    @loader.load_doc(expect_errors=False)
    def test_merged_prices(self, entries, _errors, _options_map):
        '''
        2024-09-13 price BTC    2.00 EUR
          open: 1 EUR
          high: 3 EUR
          low: 0.10 EUR
          volume: 2

        2024-09-14 price BTC    1.50 EUR
          open: 2 EUR
          high: 4 EUR
          low: 0.20 EUR
          volume: 3

        '''
        got = prices._merge_prices(entries)
        self.assertEqual(got.date, datetime.date(2024, 9, 14))
        self.assertEqual(got.meta['open'], data.Amount.from_string('1 EUR'))
        self.assertEqual(got.meta['high'], data.Amount.from_string('4 EUR'))
        self.assertEqual(got.meta['low'], data.Amount.from_string('0.10 EUR'))
        self.assertEqual(got.meta['volume'], data.D('5'))
        self.assertEqual(got.currency, 'BTC')
        self.assertEqual(got.amount, data.Amount.from_string('1.50 EUR'))

    def test_merged_empty_price_list(self):
        prices._merge_prices([])

    @loader.load_doc(expect_errors=False)
    def test_merged_single_price_point(self, entries, _errors, _options_map):
        '''
        2024-09-13 price BTC    2.00 EUR
          open: 1 EUR
          high: 3 EUR
          low: 0.10 EUR
          volume: 2
        '''
        got = prices._merge_prices(entries)
        self.assertEqual(got.date, datetime.date(2024, 9, 13))
        self.assertEqual(got.meta['open'], data.Amount.from_string('1 EUR'))
        self.assertEqual(got.meta['high'], data.Amount.from_string('3 EUR'))
        self.assertEqual(got.meta['low'], data.Amount.from_string('0.10 EUR'))
        self.assertEqual(got.meta['volume'], data.D('2'))
        self.assertEqual(got.currency, 'BTC')
        self.assertEqual(got.amount, data.Amount.from_string('2 EUR'))
