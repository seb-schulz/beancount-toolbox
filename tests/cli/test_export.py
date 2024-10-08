from os import path
import unittest

from beancount import loader
from beancount.parser import cmptest
from beancount_toolbox.cli import export
from beancount.core import data
from beancount.utils import test_utils


def fixture_path() -> str:
    return path.join(
        path.dirname(path.dirname(__file__)),
        'fixtures',
        'export',
    )


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


class TransactionOnlyConfig(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_empty_plugin_list(self, entires, errors, options_map):
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
        plugin = export.TransactionOnlyConfig(keep_directives=True)
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
        plugin = export.TransactionOnlyConfig(
            plugins=[
                export.BeancountPluginConfig(
                    module_name='beancount.plugins.split_expenses',
                    string_config='A B',
                )
            ],
            keep_directives=True,
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

    @loader.load_doc(expect_errors=False)
    def test_beancount_filter_tags(self, entires, errors, options_map):
        """
        2011-01-01 open Assets:Cash:Foobar
        2011-01-02 open Assets:Cash:Baz
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something" #foo
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        plugin = export.TransactionOnlyConfig(
            plugins=[
                export.BeancountPluginConfig(
                    module_name='beancount_toolbox.plugins.filter_tags',
                    string_config='foo',
                ),
            ],
            keep_directives=True,
        )

        new_entries, new_errors = plugin.apply(entires, options_map)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 open Assets:Cash:Foobar
            2011-01-02 open Assets:Cash:Baz
            2011-01-01 open Expenses:Misc

            2011-01-01 * "Something" #foo
              Assets:Cash:Foobar  -1.00 USD
              Expenses:Misc        1.00 USD
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=False)
    def test_with_dropped_directives(self, entires, errors, options_map):
        """
        2011-01-01 open Assets:Cash:Foobar
        2011-01-02 open Assets:Cash:Baz
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something" #foo
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        plugin = export.TransactionOnlyConfig(
            plugins=[],
            keep_directives=False,
        )

        new_entries, new_errors = plugin.apply(entires, options_map)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something" #foo
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=False)
    def test_inner_plugin_transaction_only_check(self, entires, errors,
                                                 options_map):
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

        def check(entries, _options_map):
            for e in entries:
                self.assertIsInstance(e, data.Transaction)
            return entries, []

        plugin = export.TransactionOnlyConfig(
            plugins=[export.CallableConfig(fun=check)],
            keep_directives=True,
        )

        plugin.apply(entires, options_map)


class TestExport(cmptest.TestCase):

    def test_empty_config(self):
        with test_utils.capture() as stdout:
            test_utils.run_with_args(export.main, [
                path.join(fixture_path(), 'export1.yaml'),
                path.join(fixture_path(), 'example.bean'),
            ])
        output = stdout.getvalue()

        self.assertEqualEntries(
            r"""
            2011-01-01 open Assets:Cash:Foobar
            2011-01-02 open Assets:Cash:Baz
            2011-01-01 open Expenses:Misc

            2011-01-01 * "Something" #foobar
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            output,
        )

    def test_tag_filter(self):
        with test_utils.capture() as stdout:
            test_utils.run_with_args(export.main, [
                path.join(fixture_path(), 'export2.yaml'),
                path.join(fixture_path(), 'example.bean'),
            ])
        output = stdout.getvalue()

        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something" #foobar
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            output,
        )


class Action(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_apply_keep_only_transactions(self, entires, errors, options_map):
        """
        2011-01-01 open Assets:Cash:Foobar
        2011-01-02 open Assets:Cash:Baz
        2011-01-01 open Expenses:Misc

        2011-01-01 * "Something" #foo
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.Action(
            keep_only_transactions=True)._apply_keep_only_transactions(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something" #foo
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            new_entries,
        )

        new_entries, new_errors = export.Action(
            keep_only_transactions=False)._apply_keep_only_transactions(
                entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 open Assets:Cash:Foobar
            2011-01-01 open Expenses:Misc
            2011-01-02 open Assets:Cash:Baz

            2011-01-01 * "Something" #foo
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=True)
    def test_apply_tidy_transactions(self, entires, errors, options_map):
        """
        2011-01-01 * "Something" #foo
            Assets:Cash:Foobar  -1.00 USD
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something II" #foo
            Assets:Cash:Foobar  -2.00 USD @ 1 EUR
            Assets:Cash:Foobar  -1.00 USD @ 1 EUR
            Expenses:Misc        1.00 USD

        2011-01-03 * "Something III" #foo
            Assets:Cash:Foobar  -2 ITEM {1.50 USD}
            Assets:Cash:Foobar  -1 ITEM {1.50 USD}
            Expenses:Misc        1.00 USD

        2011-01-03 * "Something III" #foo
            Assets:Cash:Foobar  -2 ITEM {1.50 USD}
            Assets:Cash:Foobar   2 ITEM {1.50 USD}
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.Action(
            keep_only_transactions=True)._apply_tidy_transactions(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -2.00 USD
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something II"
                Assets:Cash:Foobar  -3.00 USD @ 1 EUR
                Expenses:Misc        1.00 USD

            2011-01-03 * "Something III"
                Assets:Cash:Foobar  -3 ITEM {1.50 USD}
                Expenses:Misc        1.00 USD

            2011-01-03 * "Something III"
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            new_entries,
        )


class RenameAccount(cmptest.TestCase):

    @loader.load_doc(expect_errors=True)
    def test_simple_replace(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.RenameAccount(
            old='Expenses:Misc',
            new='Expenses:Foobar',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Foobar      1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Foobar      1.00 USD
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=True)
    def test_regex_replace(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.RenameAccount(
            old=r'^Exp.+sc$',
            new='Expenses:Foobar',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Foobar      1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Foobar      1.00 USD
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=True)
    def test_regex_with_template(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc:A      1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc:B      1.00 USD
        """
        new_entries, new_errors = export.RenameAccount(
            old=r'^Expenses:(?P<component>.+):A$',
            new='Expenses:{component}:C',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 USD
                Expenses:Misc:C      1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc:B      1.00 USD
            """,
            new_entries,
        )


class RenameCommodity(cmptest.TestCase):

    @loader.load_doc(expect_errors=True)
    def test_simple_replace(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.RenameCommodity(
            old='USD',
            new='EUR',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 EUR
                Expenses:Misc        1.00 EUR

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 EUR
                Expenses:Misc        1.00 EUR
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=True)
    def test_simple_replace_with_costs(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1 ITEM {2.00 USD}
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.RenameCommodity(
            old='ITEM',
            new='FOOBAR',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1 FOOBAR {2.00 USD}
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            new_entries,
        )

        new_entries, new_errors = export.RenameCommodity(
            old='USD',
            new='EUR',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1 ITEM {2.00 EUR}
                Expenses:Misc        1.00 EUR

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 EUR
                Expenses:Misc        1.00 EUR
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=True)
    def test_simple_replace_with_price(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1 ITEM @ 3.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.RenameCommodity(
            old='ITEM',
            new='FOOBAR',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1 FOOBAR @ 3.00 USD
                Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 USD
                Expenses:Misc        1.00 USD
            """,
            new_entries,
        )

        new_entries, new_errors = export.RenameCommodity(
            old='USD',
            new='EUR',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1 ITEM @ 3.00 EUR
                Expenses:Misc        1.00 EUR

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 EUR
                Expenses:Misc        1.00 EUR
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=True)
    def test_regex_replace(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc        1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc        1.00 USD
        """
        new_entries, new_errors = export.RenameCommodity(
            old=r'^U.+D$',
            new='EUR',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 EUR
                Expenses:Misc        1.00 EUR

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 EUR
                Expenses:Misc        1.00 EUR
            """,
            new_entries,
        )

    @loader.load_doc(expect_errors=True)
    def test_regex_with_template(self, entires, errors, options_map):
        """
        2011-01-01 * "Something"
            Assets:Cash:Foobar  -1.00 USD
            Expenses:Misc:A      1.00 USD

        2011-01-02 * "Something else"
            Assets:Cash:Baz     -1.00 USD
            Expenses:Misc:B      1.00 USD
        """
        new_entries, new_errors = export.RenameCommodity(
            old=r'^(?P<component>.+)$',
            new=r'TEST.{component}',
        )._apply(entires)

        self.assertEqual(0, len(new_errors))
        self.assertEqualEntries(
            r"""
            2011-01-01 * "Something"
                Assets:Cash:Foobar  -1.00 TEST.USD
                Expenses:Misc:A      1.00 TEST.USD

            2011-01-02 * "Something else"
                Assets:Cash:Baz     -1.00 TEST.USD
                Expenses:Misc:B      1.00 TEST.USD
            """,
            new_entries,
        )


if __name__ == '__main__':
    unittest.main()
