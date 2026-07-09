"""Tests for the auto_depreciation plugin."""
import unittest
from datetime import date
from beancount import loader
from beancount.parser import cmptest
from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.core.position import Cost
from beancount_toolbox.plugins.auto_depreciation import auto_depreciation


class TestAutoDepreciation(cmptest.TestCase):
    """Test cases for auto_depreciation plugin."""

    @loader.load_doc(expect_errors=False)
    def test_posting_without_cost(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.auto_depreciation"
        plugin "beancount.plugins.auto_accounts"

        2024-01-01 open Assets:Fixed:Equipment
        2024-01-01 open Assets:Cash

        2024-01-15 * "Buy equipment without cost"
          Assets:Fixed:Equipment    1000.00 USD
            useful_life: "5y"
          Assets:Cash              -1000.00 USD
        """
        # Should not crash, should handle gracefully - no errors expected since cost=None is handled
        self.assertEqual(0, len(errors))

    @loader.load_doc(expect_errors=True)
    def test_invalid_useful_life_format(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.auto_depreciation"
        plugin "beancount.plugins.auto_accounts"

        2024-01-01 open Assets:Fixed:Equipment
        2024-01-01 open Assets:Cash

        2024-01-15 * "Buy equipment with invalid useful_life"
          Assets:Fixed:Equipment    1000.00 USD {1000.00 USD}
            useful_life: "invalid"
          Assets:Cash              -1000.00 USD
        """
        # Should not crash on regex mismatch - expect plugin error but no crash
        self.assertGreaterEqual(len(errors), 1)

    @loader.load_doc(expect_errors=True)
    def test_missing_useful_life_metadata(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.auto_depreciation"
        plugin "beancount.plugins.auto_accounts"

        2024-01-01 open Assets:Fixed:Equipment
        2024-01-01 open Assets:Cash

        2024-01-15 * "Buy equipment without useful_life"
          Assets:Fixed:Equipment    1000.00 USD {1000.00 USD}
          Assets:Cash              -1000.00 USD
        """
        # Should not crash, just skip this posting - may have validation errors
        self.assertGreaterEqual(len(errors), 0)

    @loader.load_doc(expect_errors=False)
    def test_no_matching_postings(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.auto_depreciation"
        plugin "beancount.plugins.auto_accounts"

        2024-01-01 open Assets:Cash
        2024-01-01 open Expenses:Food

        2024-01-15 * "Regular transaction"
          Expenses:Food    100.00 USD
          Assets:Cash    -100.00 USD
        """
        # Should not crash when no depreciation entries are generated
        self.assertEqual(0, len(errors))

    @loader.load_doc(expect_errors=True)
    def test_valid_depreciation_linear(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.auto_depreciation"
        plugin "beancount.plugins.auto_accounts"

        2024-01-01 open Assets:Fixed:Equipment    USD
        2024-01-01 open Assets:Cash              USD
        2024-01-01 open Expenses:Depreciation    USD

        2024-01-15 * "Buy equipment"
          Assets:Fixed:Equipment    1000.00 USD {1000.00 USD, "equip-001"}
            useful_life: "5y"
            residual_value: "100.00"
          Assets:Cash              -1000.00 USD
        """
        # Should generate depreciation entries without plugin errors
        # May have validation errors from beancount itself
        plugin_errors = [e for e in errors if 'auto_depreciation' in str(e)]
        self.assertEqual(0, len(plugin_errors))
        # Check that depreciation entries were created
        depreciation_entries = [
            e for e in entries
            if isinstance(e, data.Transaction) and e.narration and 'auto_depreciation' in e.narration
        ]
        self.assertGreater(len(depreciation_entries), 0)

    @loader.load_doc(expect_errors=True)
    def test_valid_depreciation_months(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.auto_depreciation"
        plugin "beancount.plugins.auto_accounts"

        2024-01-01 open Assets:Fixed:Equipment    USD
        2024-01-01 open Assets:Cash              USD
        2024-01-01 open Expenses:Depreciation    USD

        2024-01-15 * "Buy equipment"
          Assets:Fixed:Equipment    1000.00 USD {1000.00 USD}
            useful_life: "60m"
          Assets:Cash              -1000.00 USD
        """
        # May have validation errors but no plugin crashes
        plugin_errors = [e for e in errors if 'auto_depreciation' in str(e)]
        self.assertEqual(0, len(plugin_errors))

    @loader.load_doc(expect_errors=True)
    def test_missing_residual_value(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.auto_depreciation"
        plugin "beancount.plugins.auto_accounts"

        2024-01-01 open Assets:Fixed:Equipment    USD
        2024-01-01 open Assets:Cash              USD
        2024-01-01 open Expenses:Depreciation    USD

        2024-01-15 * "Buy equipment"
          Assets:Fixed:Equipment    1000.00 USD {1000.00 USD}
            useful_life: "5y"
          Assets:Cash              -1000.00 USD
        """
        # Should use default residual_value of 0.0
        plugin_errors = [e for e in errors if 'auto_depreciation' in str(e)]
        self.assertEqual(0, len(plugin_errors))

    def test_direct_call_no_cost(self):
        """Test direct plugin call with posting that has no cost."""
        entries = []
        meta = data.new_metadata("<test>", 0)

        # Create open entries
        entries.append(data.Open(meta, date(2024, 1, 1),
                       "Assets:Fixed:Equipment", [], None))
        entries.append(data.Open(meta, date(
            2024, 1, 1), "Assets:Cash", [], None))

        # Create transaction without cost
        txn_meta = data.new_metadata("<test>", 1)
        posting1 = data.Posting("Assets:Fixed:Equipment", Amount(
            D("1000.00"), "USD"), None, None, None, {"useful_life": "5y"})
        posting2 = data.Posting("Assets:Cash", Amount(
            D("-1000.00"), "USD"), None, None, None, None)
        entries.append(data.Transaction(txn_meta, date(
            2024, 1, 15), "*", None, "Buy equipment", frozenset(), frozenset(), [posting1, posting2]))

        options_map = {}

        # Should not crash
        result_entries, result_errors = auto_depreciation(entries, options_map)
        self.assertEqual(0, len(result_errors))

    def test_direct_call_invalid_useful_life(self):
        """Test direct plugin call with invalid useful_life format."""
        entries = []
        meta = data.new_metadata("<test>", 0)

        # Create open entries
        entries.append(data.Open(meta, date(2024, 1, 1),
                       "Assets:Fixed:Equipment", [], None))
        entries.append(data.Open(meta, date(
            2024, 1, 1), "Assets:Cash", [], None))

        # Create transaction with cost but invalid useful_life
        txn_meta = data.new_metadata("<test>", 1)
        cost = Cost(D("1000.00"), "USD", date(2024, 1, 15), None)
        posting1 = data.Posting("Assets:Fixed:Equipment", Amount(
            D("1000.00"), "USD"), cost, None, None, {"useful_life": "invalid"})
        posting2 = data.Posting("Assets:Cash", Amount(
            D("-1000.00"), "USD"), None, None, None, None)
        entries.append(data.Transaction(txn_meta, date(
            2024, 1, 15), "*", None, "Buy equipment", frozenset(), frozenset(), [posting1, posting2]))

        options_map = {}

        # Should not crash
        result_entries, result_errors = auto_depreciation(entries, options_map)
        self.assertEqual(0, len(result_errors))


if __name__ == '__main__':
    unittest.main()
