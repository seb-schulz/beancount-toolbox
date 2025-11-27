"""Tests for weight directive parsing."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from beancount_toolbox.ext.portfolio_monitor.weight_parsing import (
    find_accounts_with_weights,
    infer_bucket,
    parse_weight_directives,
)


class TestFindAccountsWithWeights:
    """Test finding accounts with weight directives."""

    def test_empty_entries(self):
        """No entries returns empty set."""
        assert find_accounts_with_weights([]) == set()

    def test_only_portfolio_weight_directives(self):
        """Only portfolio-weight directives are included."""
        entry1 = Mock(type='portfolio-weight', date=date(2024, 1, 1))
        entry1.values = [Mock(value='Assets:US')]

        entry2 = Mock(type='other-custom', date=date(2024, 1, 1))
        entry2.values = [Mock(value='Assets:Intl')]

        result = find_accounts_with_weights([entry1, entry2])
        assert result == {'Assets:US'}

    def test_date_filtering(self):
        """Directives after end_date are excluded."""
        entry1 = Mock(type='portfolio-weight', date=date(2023, 12, 31))
        entry1.values = [Mock(value='Assets:US')]

        entry2 = Mock(type='portfolio-weight', date=date(2024, 1, 2))
        entry2.values = [Mock(value='Assets:Intl')]

        result = find_accounts_with_weights([entry1, entry2], date(2024, 1, 1))
        assert result == {'Assets:US'}

    def test_none_end_date_includes_all(self):
        """None end_date includes all directives."""
        entry1 = Mock(type='portfolio-weight', date=date(2023, 1, 1))
        entry1.values = [Mock(value='Assets:US')]

        entry2 = Mock(type='portfolio-weight', date=date(2025, 1, 1))
        entry2.values = [Mock(value='Assets:Intl')]

        result = find_accounts_with_weights([entry1, entry2], None)
        assert result == {'Assets:US', 'Assets:Intl'}


class TestInferBucket:
    """Test bucket inference logic."""

    def test_no_ancestor_uses_root(self):
        """Account with no ancestor directive uses root."""
        accounts = {'Assets:US', 'Assets:Intl'}
        result = infer_bucket('Assets:CA:Cash', accounts, 'Assets')
        assert result == 'Assets'

    def test_immediate_parent_with_directive(self):
        """Use immediate parent if it has directive."""
        accounts = {'Assets:US', 'Assets:US:Vanguard'}
        result = infer_bucket('Assets:US:Vanguard:VTSAX', accounts, 'Assets')
        assert result == 'Assets:US:Vanguard'

    def test_grandparent_with_directive(self):
        """Use grandparent if parent has no directive."""
        accounts = {'Assets:US'}
        result = infer_bucket('Assets:US:Vanguard:VTSAX', accounts, 'Assets')
        assert result == 'Assets:US'

    def test_root_account_itself(self):
        """Root account returns itself when no directives."""
        accounts = set()
        result = infer_bucket('Assets:US', accounts, 'Assets')
        assert result == 'Assets'


class TestParseWeightDirectives:
    """Test full directive parsing."""

    def test_percentage_weight(self):
        """Parse percentage weight."""
        entry = Mock(type='portfolio-weight', date=date(2024, 1, 1))
        entry.values = [
            Mock(value='Assets:US:ITOT'),
            Mock(value=Decimal('0.6'), number=None, currency=None)
        ]

        result = parse_weight_directives([entry], 'Assets', 'USD')
        assert result == {
            'Assets': {
                'Assets:US:ITOT': Decimal('0.6')
            }
        }

    def test_absolute_amount_weight(self):
        """Parse absolute amount weight."""
        entry = Mock(type='portfolio-weight', date=date(2024, 1, 1))
        entry.values = [
            Mock(value='Assets:US:Cash'),
            Mock(value=None, number=Decimal('5000'), currency='USD')
        ]

        result = parse_weight_directives([entry], 'Assets', 'USD')
        assert result == {
            'Assets': {
                'Assets:US:Cash': (Decimal('5000'), 'USD')
            }
        }

    def test_explicit_bucket(self):
        """Parse directive with explicit bucket."""
        entry = Mock(type='portfolio-weight', date=date(2024, 1, 1))
        entry.values = [
            Mock(value='Assets:US:Vanguard:VTSAX'),
            Mock(value=Decimal('0.4'), number=None, currency=None),
            Mock(value='Assets:US')
        ]

        result = parse_weight_directives([entry], 'Assets', 'USD')
        assert result == {
            'Assets:US': {
                'Assets:US:Vanguard:VTSAX': Decimal('0.4')
            }
        }

    def test_wrong_currency_raises(self):
        """Wrong currency raises ValueError."""
        entry = Mock(type='portfolio-weight', date=date(2024, 1, 1))
        entry.values = [
            Mock(value='Assets:US:Cash'),
            Mock(value=None, number=Decimal('5000'), currency='EUR')
        ]

        with pytest.raises(ValueError, match="only 'USD' is allowed"):
            parse_weight_directives([entry], 'Assets', 'USD')

    def test_automatic_bucket_inference(self):
        """Test bucket inference from ancestors."""
        # Entry 1: Parent with directive
        entry1 = Mock(type='portfolio-weight', date=date(2024, 1, 1))
        entry1.values = [
            Mock(value='Assets:US:Vanguard'),
            Mock(value=Decimal('0.65'), number=None, currency=None)
        ]

        # Entry 2: Child without explicit bucket (should infer Vanguard)
        entry2 = Mock(type='portfolio-weight', date=date(2024, 1, 1))
        entry2.values = [
            Mock(value='Assets:US:Vanguard:Cash'),
            Mock(value=Decimal('0.2'), number=None, currency=None)
        ]

        result = parse_weight_directives([entry1, entry2], 'Assets', 'USD')

        # Vanguard uses root (Assets) as bucket
        assert 'Assets' in result
        assert result['Assets']['Assets:US:Vanguard'] == Decimal('0.65')

        # Cash infers Vanguard as bucket
        assert 'Assets:US:Vanguard' in result
        assert result['Assets:US:Vanguard']['Assets:US:Vanguard:Cash'] == Decimal('0.2')

    def test_date_filtering_excludes_future(self):
        """Future directives are excluded."""
        entry1 = Mock(type='portfolio-weight', date=date(2023, 1, 1))
        entry1.values = [
            Mock(value='Assets:US:ITOT'),
            Mock(value=Decimal('0.5'), number=None, currency=None)
        ]

        entry2 = Mock(type='portfolio-weight', date=date(2024, 6, 1))
        entry2.values = [
            Mock(value='Assets:US:VBMPX'),
            Mock(value=Decimal('0.3'), number=None, currency=None)
        ]

        result = parse_weight_directives([entry1, entry2], 'Assets', 'USD', date(2024, 1, 1))

        # Only entry1 should be included
        assert 'Assets' in result
        assert 'Assets:US:ITOT' in result['Assets']
        assert 'Assets:US:VBMPX' not in result['Assets']
