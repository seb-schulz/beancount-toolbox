from beancount import loader

from beancount.parser import cmptest
from beancount_toolbox.plugins import prices
from tests import _helper


class TestDocuments(cmptest.TestCase):

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
        2009-01-01 commodity BTC
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
            2009-01-01 commodity BTC

            2024-09-12 price BTC    52497.29 EUR
            2024-09-13 price BTC    54667.16 EUR
            2024-09-14 price BTC    54149.93 EUR
            2024-09-15 price BTC    53354.50 EUR
            2024-09-16 price BTC    52289.82 EUR
            2024-09-17 price BTC    54228.27 EUR
            2024-09-18 price BTC    55557.73 EUR
            2024-09-19 price BTC    56395.45 EUR
            2024-09-20 price BTC    56627.89 EUR
            2024-09-21 price BTC    56782.42 EUR
            ''', got_entries)

        self.assertEqual(got_entries[-1].meta.get('open', ''), '56627.89 EUR')
        self.assertEqual(got_entries[-1].meta.get('high', ''), '56930.52 EUR')
        self.assertEqual(got_entries[-1].meta.get('low', ''), '56246.83 EUR')
        self.assertEqual(got_entries[-1].meta.get('volume', ''), '4101671')

    @loader.load_doc(expect_errors=False)
    def test_commodity_abc(self, entries, _errors, options_map):
        """
        option "operating_currency" "EUR"
        plugin "beancount.plugins.auto_accounts"
        2009-01-01 commodity A.B.C
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
            2009-01-01 commodity A.B.C

            2024-08-13 price A.B.C  66.400 EUR
            2024-08-14 price A.B.C  66.000 EUR
            2024-08-15 price A.B.C  66.100 EUR
            2024-08-16 price A.B.C  66.100 EUR
            2024-08-19 price A.B.C  66.200 EUR
            2024-08-20 price A.B.C  66.000 EUR
            2024-08-21 price A.B.C  66.200 EUR
            2024-08-22 price A.B.C  66.200 EUR
            2024-08-23 price A.B.C  65.800 EUR
            2024-08-26 price A.B.C  66.200 EUR
            ''', got_entries)

        self.assertEqual(got_entries[-1].meta.get('open', ''), '65.800 EUR')
        self.assertEqual(got_entries[-1].meta.get('high', ''), '66.300 EUR')
        self.assertEqual(got_entries[-1].meta.get('low', ''), '65.300 EUR')
        self.assertEqual(got_entries[-1].meta.get('volume', ''), '1230')

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
        2009-01-01 commodity BTC
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
            2009-01-01 commodity BTC
            2024-09-12 price BTC    52497.29 USD
            2024-09-13 price BTC    54667.16 EUR
            2024-09-14 price BTC    54149.93 USD
            2024-09-16 price BTC    52289.82 EUR
            2024-09-17 price BTC    54228.27 EUR
            2024-09-18 price BTC    55557.73 EUR
            2024-09-19 price BTC    56395.45 EUR
            2024-09-20 price BTC    56627.89 EUR
            2024-09-21 price BTC    56782.42 EUR
            ''', got_entries)
