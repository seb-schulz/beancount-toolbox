import unittest

from beancount import loader
from beancount.parser import cmptest
from beancount_toolbox.cli import export


class BeancountPluginConfig(cmptest.TestCase):

    @loader.load_doc(expect_errors=True)
    def test_beancount_auto_accounts(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        plugin = export.BeancountPluginConfig(
            module_name='beancount.plugins.auto_accounts')

        new_entries, new_errors = plugin.apply(entires, options_map)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 open Assets:Cash:Foobar
            2011-01-02 open Assets:Cash:Baz
            2011-01-01 open Expenses:Misc

            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=False)
    def test_beancount_split_expenses(self, entires, errors, options_map):
        """
        2011-01-01 open Assets:Cash:Foobar
        2011-01-02 open Assets:Cash:Baz
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        plugin = export.BeancountPluginConfig(
            module_name='beancount.plugins.split_expenses',
            string_config='A B',
        )

        new_entries, new_errors = plugin.apply(entires, options_map)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 open Assets:Cash:Foobar
            2011-01-02 open Assets:Cash:Baz
            2011-01-01 open Expenses:Misc
            2011-01-01 open Expenses:Misc:A
            2011-01-01 open Expenses:Misc:B

            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc:A      0.50 USD
                Expenses:Misc:B      0.50 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc:A      0.50 USD
                Expenses:Misc:B      0.50 USD
            """,
            new_entries,
        )


if __name__ == '__main__':
    unittest.main()
