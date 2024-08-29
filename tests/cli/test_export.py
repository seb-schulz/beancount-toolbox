from beancount import loader
from beancount.parser import cmptest
from beancount_toolbox.cli import export


class ExecPlugin(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_empty_execution(self, entires, errors, options_map):
        """
        2011-01-01 open Assets:Cash:Foobar
        2011-01-01 open Assets:Cash:Baz
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.exec_plugin(
            entires,
            options_map,
            None,
        )

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 open Assets:Cash:Foobar
            2011-01-01 open Assets:Cash:Baz
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

    @loader.load_doc(expect_errors=True)
    def test_empty_execution(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.exec_plugin(
            entires,
            options_map,
            export.PluginConfig(module_name='beancount.plugins.auto_accounts'),
        )

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
