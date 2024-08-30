import unittest
from beancount import loader
from beancount.parser import cmptest


class TestDocuments(cmptest.TestCase):

    @unittest.SkipTest
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
        self.assertEqual(3, len(entries))

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


if __name__ == '__main__':
    unittest.main()
