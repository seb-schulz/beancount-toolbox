from beancount import loader
from beancount.parser import cmptest


class SpreadPadOnly(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_spread_one_pad_auto_no_error(self, entires, errors, options_map):
        """
            plugin "beancount_toolbox.plugins.tag_component" "Foobar"

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
        self.assertEqual(0, len(errors))
        self.assertEqual(5, len(entires))
        self.assertEqualEntries(
            r'''
            2011-01-01 open Assets:Cash:Foobar
            2011-01-01 open Assets:Cash:Baz
            2011-01-01 open Expenses:Misc

            2011-01-01 * "Something" #foobar
              Assets:Cash:Foobar  -1.00 USD
              Expenses:Misc        1.00 USD

            2011-01-02 * "Something else"
              Assets:Cash:Baz     -1.00 USD
              Expenses:Misc        1.00 USD
        ''', entires)
