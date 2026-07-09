import unittest
from beancount import loader
from beancount.parser import cmptest
from beancount.core import data


class TestDocuments(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_valid_beanfile_without_tags(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.filter_tags" "foo"
        plugin "beancount.plugins.auto_accounts"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqualEntries(
            '''
            plugin "beancount_toolbox.plugins.filter_tags" "foo"
            plugin "beancount.plugins.auto_accounts"
            ''',
            entries,
        )

    @loader.load_doc(expect_errors=False)
    def test_filtered_beanfile(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.filter_tags" "foo"
        plugin "beancount.plugins.auto_accounts"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #bar
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD

        2011-05-18 * "Something" #foo
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqualEntries(
            '''
            2011-05-18 open Expenses:Food
            2011-05-18 open Assets:Other

            2011-05-18 * "Something" #foo
              Expenses:Food   1.00 USD
              Assets:Other   -1.00 USD
            ''',
            entries,
        )

    @loader.load_doc(expect_errors=False)
    def test_filtered_beanfile_without_auto_open(self, entries, errors,
                                                 options_map):
        """
        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #bar
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD

        2011-05-18 * "Something" #foo
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        from beancount_toolbox.plugins.filter_tags import filter_tags
        entries, errors = filter_tags(entries, options_map, "foo")

        self.assertEqual(0, len(errors))
        self.assertEqualEntries(
            '''
            2011-05-18 * "Something" #foo
              Expenses:Food   1.00 USD
              Assets:Other   -1.00 USD
            ''',
            entries,
        )

    @loader.load_doc(expect_errors=False)
    def test_filtered_beanfile_multiple_tags(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.filter_tags" "foo bar"
        plugin "beancount.plugins.auto_accounts"

        2011-05-17 * "Only bar" #bar
            Expenses:Food   1.00 USD
            Assets:Other   -1.00 USD

        2011-05-18 * "Only foo" #foo
            Expenses:Food   1.00 USD
            Assets:Other   -1.00 USD

        2011-05-19 * "Both" #foo #bar
            Expenses:Food   1.00 USD
            Assets:Other   -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(
            1, len([e for e in entries if isinstance(e, data.Transaction)]))


if __name__ == '__main__':
    unittest.main()
