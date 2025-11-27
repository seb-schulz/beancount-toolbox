"""Tests for portfolio weight allocation algorithm."""
import pytest
from decimal import Decimal
from fava.core.tree import TreeNode

from beancount_toolbox.ext.portfolio_monitor.weight_allocation import (
    is_ancestor,
    preprocess_weights,
    compute_weights,
    weight_list,
)


class TestIsAncestor:
    """Test the is_ancestor helper function."""

    def test_same_account(self):
        """An account is its own ancestor."""
        assert is_ancestor("Assets", "Assets") is True

    def test_direct_child(self):
        """Direct child relationship."""
        assert is_ancestor("Assets", "Assets:Checking") is True

    def test_nested_child(self):
        """Nested child relationship."""
        assert is_ancestor("Assets", "Assets:US:ETrade:ITOT") is True

    def test_not_ancestor(self):
        """Unrelated accounts."""
        assert is_ancestor("Assets", "Liabilities:Loan") is False

    def test_sibling_accounts(self):
        """Sibling accounts are not ancestors."""
        assert is_ancestor("Assets:Checking", "Assets:Savings") is False


class TestWeightListBasic:
    """Test basic weight allocation scenarios."""

    def test_single_leaf_node(self):
        """Single leaf node gets full weight."""
        root = TreeNode("Assets")
        weights = weight_list(root, {})
        assert weights == {"Assets": Decimal(1)}

    def test_equal_distribution_two_children(self):
        """Two children with no custom weights get equal distribution."""
        root = TreeNode("Assets")
        child1 = TreeNode("Assets:Checking")
        child2 = TreeNode("Assets:Savings")
        root.children = [child1, child2]

        weights = weight_list(root, {})
        assert weights == {
            "Assets:Checking": Decimal("0.5"),
            "Assets:Savings": Decimal("0.5")
        }

    def test_equal_distribution_three_children(self):
        """Three children with no custom weights get equal distribution."""
        root = TreeNode("Assets:US")
        child1 = TreeNode("Assets:US:ITOT")
        child2 = TreeNode("Assets:US:VBMPX")
        child3 = TreeNode("Assets:US:VTI")
        root.children = [child1, child2, child3]

        weights = weight_list(root, {})

        expected_weight = Decimal(1) / Decimal(3)
        assert weights == {
            "Assets:US:ITOT": expected_weight,
            "Assets:US:VBMPX": expected_weight,
            "Assets:US:VTI": expected_weight
        }


class TestWeightListCustomWeights:
    """Test custom weight allocation scenarios."""

    def test_single_custom_weight(self):
        """One child with custom weight, others share remainder."""
        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        child3 = TreeNode("Assets:US:ETrade:VTI")
        root.children = [child1, child2, child3]

        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.2")
            }
        }

        weights = weight_list(root, weight_entries)

        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.2"),
            "Assets:US:ETrade:VBMPX": Decimal("0.4"),
            "Assets:US:ETrade:VTI": Decimal("0.4")
        }

    def test_multiple_custom_weights(self):
        """Multiple children with custom weights, one shares remainder."""
        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        child3 = TreeNode("Assets:US:ETrade:VTI")
        root.children = [child1, child2, child3]

        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.2"),
                "Assets:US:ETrade:VBMPX": Decimal("0.3")
            }
        }

        weights = weight_list(root, weight_entries)

        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.2"),
            "Assets:US:ETrade:VBMPX": Decimal("0.3"),
            "Assets:US:ETrade:VTI": Decimal("0.5")
        }

    def test_all_children_custom_weights(self):
        """All children have custom weights summing to 1.0."""
        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        child3 = TreeNode("Assets:US:ETrade:VTI")
        root.children = [child1, child2, child3]

        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.2"),
                "Assets:US:ETrade:VBMPX": Decimal("0.3"),
                "Assets:US:ETrade:VTI": Decimal("0.5")
            }
        }

        weights = weight_list(root, weight_entries)

        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.2"),
            "Assets:US:ETrade:VBMPX": Decimal("0.3"),
            "Assets:US:ETrade:VTI": Decimal("0.5")
        }


class TestWeightListHierarchical:
    """Test hierarchical weight composition."""

    def test_two_level_hierarchy(self):
        """Test weight allocation in a two-level hierarchy."""
        root = TreeNode("Assets:US")
        etrade = TreeNode("Assets:US:ETrade")
        vanguard = TreeNode("Assets:US:Vanguard")
        root.children = [etrade, vanguard]

        itot = TreeNode("Assets:US:ETrade:ITOT")
        vbmpx = TreeNode("Assets:US:ETrade:VBMPX")
        etrade.children = [itot, vbmpx]

        vtsax = TreeNode("Assets:US:Vanguard:VTSAX")
        vanguard.children = [vtsax]

        # ETrade gets 0.3 of Assets:US
        # Within ETrade, ITOT gets 0.5 (so 0.5 * 0.3 = 0.15 of total)
        weight_entries = {
            "Assets:US": {
                "Assets:US:ETrade:ITOT": Decimal("0.3")
            },
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.5")
            }
        }

        weights = weight_list(root, weight_entries)

        # ETrade subtree gets 0.3 total
        # Within ETrade: ITOT=0.5*0.3=0.15, VBMPX=0.5*0.3=0.15
        # Vanguard gets remaining 0.7
        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.15"),
            "Assets:US:ETrade:VBMPX": Decimal("0.15"),
            "Assets:US:Vanguard:VTSAX": Decimal("0.7")
        }


class TestWeightListValidation:
    """Test validation and error cases."""

    def test_weight_exceeds_one(self):
        """Weight > 1.0 should raise error."""
        root = TreeNode("Assets")
        child = TreeNode("Assets:Checking")
        root.children = [child]

        weight_entries = {
            "Assets": {
                "Assets:Checking": Decimal("1.5")
            }
        }

        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            weight_list(root, weight_entries)

    def test_negative_weight(self):
        """Negative weight should raise error."""
        root = TreeNode("Assets")
        child = TreeNode("Assets:Checking")
        root.children = [child]

        weight_entries = {
            "Assets": {
                "Assets:Checking": Decimal("-0.1")
            }
        }

        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            weight_list(root, weight_entries)

    def test_weights_sum_exceeds_one(self):
        """Total custom weights > 1.0 should raise error."""
        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        root.children = [child1, child2]

        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.6"),
                "Assets:US:ETrade:VBMPX": Decimal("0.6")
            }
        }

        with pytest.raises(ValueError, match="exceed 1.0: 1.2"):
            weight_list(root, weight_entries)

    def test_account_not_in_tree(self):
        """Weight for non-existent account should raise error."""
        root = TreeNode("Assets")
        child = TreeNode("Assets:Checking")
        root.children = [child]

        weight_entries = {
            "Assets": {
                "Assets:NonExistent": Decimal("0.5")
            }
        }

        with pytest.raises(ValueError, match="not found in tree"):
            weight_list(root, weight_entries)

    def test_bucket_not_ancestor(self):
        """Bucket must be ancestor of account."""
        root = TreeNode("Assets")
        checking = TreeNode("Assets:Checking")
        savings = TreeNode("Assets:Savings")
        root.children = [checking, savings]

        weight_entries = {
            "Assets:Checking": {  # Bucket
                "Assets:Savings": Decimal("0.5")  # Not a descendant
            }
        }

        with pytest.raises(ValueError, match="not ancestor"):
            weight_list(root, weight_entries)

    def test_all_children_weighted_but_sum_less_than_one(self):
        """All children with custom weights summing < 1.0 should raise error."""
        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        root.children = [child1, child2]

        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.3"),
                "Assets:US:ETrade:VBMPX": Decimal("0.4")
            }
        }

        with pytest.raises(ValueError, match="leaving .* unallocated"):
            weight_list(root, weight_entries)


class TestWeightListAutoBucketInference:
    """Test automatic bucket inference from ancestor directives."""

    def test_auto_bucket_from_parent_directive(self):
        """Child without explicit bucket uses parent with directive as bucket."""
        # Tree:
        #   Assets:US:Vanguard
        #     ├── Cash
        #     ├── VTSAX
        #     └── VTIAX
        root = TreeNode("Assets:US:Vanguard")
        cash = TreeNode("Assets:US:Vanguard:Cash")
        vtsax = TreeNode("Assets:US:Vanguard:VTSAX")
        vtiax = TreeNode("Assets:US:Vanguard:VTIAX")
        root.children = [cash, vtsax, vtiax]

        # Simulating automatic bucket inference:
        # Directive: Assets:US:Vanguard:Cash 0.2 (no explicit bucket)
        # Since parent Assets:US:Vanguard has a weight directive,
        # Cash should use Vanguard as bucket (not root_account)
        weight_entries = {
            "Assets:US:Vanguard": {
                "Assets:US:Vanguard:Cash": Decimal("0.2")
            }
        }

        weights = weight_list(root, weight_entries)

        # Cash gets 20% of Vanguard's allocation
        # Siblings VTSAX and VTIAX share remaining 80% equally (40% each)
        assert weights == {
            "Assets:US:Vanguard:Cash": Decimal("0.2"),
            "Assets:US:Vanguard:VTSAX": Decimal("0.4"),
            "Assets:US:Vanguard:VTIAX": Decimal("0.4")
        }

    def test_auto_bucket_multi_level(self):
        """Multi-level hierarchy with automatic bucket inference."""
        # Tree:
        #   Assets:US
        #     ├── Vanguard
        #     │   ├── Cash
        #     │   └── VTSAX
        #     └── ETrade
        #         └── ITOT
        root = TreeNode("Assets:US")
        vanguard = TreeNode("Assets:US:Vanguard")
        etrade = TreeNode("Assets:US:ETrade")
        cash = TreeNode("Assets:US:Vanguard:Cash")
        vtsax = TreeNode("Assets:US:Vanguard:VTSAX")
        itot = TreeNode("Assets:US:ETrade:ITOT")

        root.children = [vanguard, etrade]
        vanguard.children = [cash, vtsax]
        etrade.children = [itot]

        # Simulating:
        # 1. Assets:US:Vanguard 0.65 → bucket is Assets:US (root)
        # 2. Assets:US:Vanguard:Cash 0.2 → bucket is Assets:US:Vanguard (closest ancestor)
        weight_entries = {
            "Assets:US": {
                "Assets:US:Vanguard": Decimal("0.65")
            },
            "Assets:US:Vanguard": {
                "Assets:US:Vanguard:Cash": Decimal("0.2")
            }
        }

        weights = weight_list(root, weight_entries)

        # Vanguard gets 65% of Assets:US, ETrade gets remaining 35%
        # Within Vanguard: Cash gets 20% of 0.65 = 0.13
        #                  VTSAX gets 80% of 0.65 = 0.52
        # ETrade's single child ITOT gets all of 0.35
        assert weights == {
            "Assets:US:Vanguard:Cash": Decimal("0.13"),
            "Assets:US:Vanguard:VTSAX": Decimal("0.52"),
            "Assets:US:ETrade:ITOT": Decimal("0.35")
        }


class TestWeightListComplexScenarios:
    """Test complex real-world scenarios."""

    def test_deep_hierarchy_with_mixed_weights(self):
        """Test deep hierarchy with custom weights at multiple levels."""
        # Assets
        #   ├── US
        #   │   ├── ETrade
        #   │   │   ├── ITOT
        #   │   │   └── VBMPX
        #   │   └── Vanguard
        #   │       └── VTSAX
        #   └── International
        #       └── VXUS

        root = TreeNode("Assets")
        us = TreeNode("Assets:US")
        intl = TreeNode("Assets:International")
        root.children = [us, intl]

        etrade = TreeNode("Assets:US:ETrade")
        vanguard = TreeNode("Assets:US:Vanguard")
        us.children = [etrade, vanguard]

        itot = TreeNode("Assets:US:ETrade:ITOT")
        vbmpx = TreeNode("Assets:US:ETrade:VBMPX")
        etrade.children = [itot, vbmpx]

        vtsax = TreeNode("Assets:US:Vanguard:VTSAX")
        vanguard.children = [vtsax]

        vxus = TreeNode("Assets:International:VXUS")
        intl.children = [vxus]

        # ITOT gets 60% of total, International gets 40%
        # Within US:ETrade, ITOT gets 70% of ETrade's allocation
        weight_entries = {
            "Assets": {
                "Assets:US:ETrade:ITOT": Decimal("0.6"),  # ITOT gets 60% absolute
                "Assets:International:VXUS": Decimal("0.4")  # International gets 40%
            },
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.7")  # ITOT gets 70% of ETrade
            }
        }

        weights = weight_list(root, weight_entries)

        # With ITOT needing 0.6 and being in ETrade:
        # - US subtree gets 0.6 (all to ETrade since ITOT needs 0.6)
        # - Within ETrade (0.6 total): ITOT=0.7*0.6=0.42, VBMPX=0.3*0.6=0.18
        # - International gets 0.4
        # - Vanguard gets 0 (no weight specified, ETrade took all of US)
        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.42"),
            "Assets:US:ETrade:VBMPX": Decimal("0.18"),
            "Assets:US:Vanguard:VTSAX": Decimal("0.0"),
            "Assets:International:VXUS": Decimal("0.4")
        }


class TestAbsoluteAmountWeights:
    """Test absolute amount weight conversion and allocation."""

    def test_single_absolute_amount(self):
        """Single child with absolute amount, others share remainder."""
        from beancount_toolbox.ext.portfolio_monitor import (
            calculate_bucket_total,
            convert_amounts_to_percentages
        )
        from unittest.mock import Mock, MagicMock
        from fava.core.inventory import CounterInventory

        # Create mock tree structure
        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        child3 = TreeNode("Assets:US:ETrade:VTI")
        root.children = [child1, child2, child3]

        # Mock balance_children for bucket total = 10000 USD
        mock_balance = MagicMock(spec=CounterInventory)
        mock_simple = MagicMock()
        mock_simple.get.return_value = Decimal("10000")
        mock_balance.reduce.return_value = mock_simple
        root.balance_children = mock_balance

        account_map = {
            "Assets:US:ETrade": root,
            "Assets:US:ETrade:ITOT": child1,
            "Assets:US:ETrade:VBMPX": child2,
            "Assets:US:ETrade:VTI": child3
        }

        # Absolute amount: ITOT gets 2000 USD (= 20% of 10000)
        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": (Decimal("2000"), "USD")
            }
        }

        mock_ledger = Mock()
        mock_ledger.prices = Mock()

        converted = convert_amounts_to_percentages(
            weight_entries, account_map, "USD", mock_ledger
        )

        # Should convert to 0.2 (20%)
        assert converted == {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.2")
            }
        }

        # Now test with weight_list
        weights = weight_list(root, converted)
        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.2"),
            "Assets:US:ETrade:VBMPX": Decimal("0.4"),
            "Assets:US:ETrade:VTI": Decimal("0.4")
        }

    def test_mixed_absolute_and_percentage(self):
        """Mix of absolute amounts and percentage weights."""
        from beancount_toolbox.ext.portfolio_monitor import convert_amounts_to_percentages
        from unittest.mock import Mock, MagicMock
        from fava.core.inventory import CounterInventory

        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        child3 = TreeNode("Assets:US:ETrade:VTI")
        root.children = [child1, child2, child3]

        # Mock balance_children for bucket total = 10000 USD
        mock_balance = MagicMock(spec=CounterInventory)
        mock_simple = MagicMock()
        mock_simple.get.return_value = Decimal("10000")
        mock_balance.reduce.return_value = mock_simple
        root.balance_children = mock_balance

        account_map = {
            "Assets:US:ETrade": root,
            "Assets:US:ETrade:ITOT": child1,
            "Assets:US:ETrade:VBMPX": child2,
            "Assets:US:ETrade:VTI": child3
        }

        # Mixed: ITOT gets 2000 USD (20%), VBMPX gets 30%
        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": (Decimal("2000"), "USD"),
                "Assets:US:ETrade:VBMPX": Decimal("0.3")
            }
        }

        mock_ledger = Mock()
        mock_ledger.prices = Mock()

        converted = convert_amounts_to_percentages(
            weight_entries, account_map, "USD", mock_ledger
        )

        # Should convert amounts to percentages, keep percentages as-is
        assert converted == {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.2"),
                "Assets:US:ETrade:VBMPX": Decimal("0.3")
            }
        }

        weights = weight_list(root, converted)
        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.2"),
            "Assets:US:ETrade:VBMPX": Decimal("0.3"),
            "Assets:US:ETrade:VTI": Decimal("0.5")
        }

    def test_amount_exceeds_bucket_total(self):
        """Absolute amount exceeding bucket total should raise error."""
        from beancount_toolbox.ext.portfolio_monitor import convert_amounts_to_percentages
        from unittest.mock import Mock, MagicMock
        from fava.core.inventory import CounterInventory

        root = TreeNode("Assets:US:ETrade")
        child = TreeNode("Assets:US:ETrade:ITOT")
        root.children = [child]

        # Mock balance_children for bucket total = 1000 USD
        mock_balance = MagicMock(spec=CounterInventory)
        mock_simple = MagicMock()
        mock_simple.get.return_value = Decimal("1000")
        mock_balance.reduce.return_value = mock_simple
        root.balance_children = mock_balance

        account_map = {
            "Assets:US:ETrade": root,
            "Assets:US:ETrade:ITOT": child
        }

        # Amount exceeds total: 1500 > 1000
        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": (Decimal("1500"), "USD")
            }
        }

        mock_ledger = Mock()

        with pytest.raises(ValueError, match="exceeds bucket.*total"):
            convert_amounts_to_percentages(
                weight_entries, account_map, "USD", mock_ledger
            )

    def test_bucket_with_zero_total(self):
        """Bucket with zero total should raise error for absolute amounts."""
        from beancount_toolbox.ext.portfolio_monitor import convert_amounts_to_percentages
        from unittest.mock import Mock, MagicMock
        from fava.core.inventory import CounterInventory

        root = TreeNode("Assets:US:ETrade")
        child = TreeNode("Assets:US:ETrade:ITOT")
        root.children = [child]

        # Mock balance_children for bucket total = 0 USD
        mock_balance = MagicMock(spec=CounterInventory)
        mock_simple = MagicMock()
        mock_simple.get.return_value = Decimal("0")
        mock_balance.reduce.return_value = mock_simple
        root.balance_children = mock_balance

        account_map = {
            "Assets:US:ETrade": root,
            "Assets:US:ETrade:ITOT": child
        }

        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": (Decimal("1000"), "USD")
            }
        }

        mock_ledger = Mock()

        with pytest.raises(ValueError, match="zero total value"):
            convert_amounts_to_percentages(
                weight_entries, account_map, "USD", mock_ledger
            )

    def test_all_children_absolute_amounts(self):
        """All children with absolute amounts summing to bucket total."""
        from beancount_toolbox.ext.portfolio_monitor import convert_amounts_to_percentages
        from unittest.mock import Mock, MagicMock
        from fava.core.inventory import CounterInventory

        root = TreeNode("Assets:US:ETrade")
        child1 = TreeNode("Assets:US:ETrade:ITOT")
        child2 = TreeNode("Assets:US:ETrade:VBMPX")
        child3 = TreeNode("Assets:US:ETrade:VTI")
        root.children = [child1, child2, child3]

        # Mock balance_children for bucket total = 10000 USD
        mock_balance = MagicMock(spec=CounterInventory)
        mock_simple = MagicMock()
        mock_simple.get.return_value = Decimal("10000")
        mock_balance.reduce.return_value = mock_simple
        root.balance_children = mock_balance

        account_map = {
            "Assets:US:ETrade": root,
            "Assets:US:ETrade:ITOT": child1,
            "Assets:US:ETrade:VBMPX": child2,
            "Assets:US:ETrade:VTI": child3
        }

        # All absolute amounts: 2000 + 3000 + 5000 = 10000
        weight_entries = {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": (Decimal("2000"), "USD"),
                "Assets:US:ETrade:VBMPX": (Decimal("3000"), "USD"),
                "Assets:US:ETrade:VTI": (Decimal("5000"), "USD")
            }
        }

        mock_ledger = Mock()

        converted = convert_amounts_to_percentages(
            weight_entries, account_map, "USD", mock_ledger
        )

        assert converted == {
            "Assets:US:ETrade": {
                "Assets:US:ETrade:ITOT": Decimal("0.2"),
                "Assets:US:ETrade:VBMPX": Decimal("0.3"),
                "Assets:US:ETrade:VTI": Decimal("0.5")
            }
        }

        weights = weight_list(root, converted)
        assert weights == {
            "Assets:US:ETrade:ITOT": Decimal("0.2"),
            "Assets:US:ETrade:VBMPX": Decimal("0.3"),
            "Assets:US:ETrade:VTI": Decimal("0.5")
        }
