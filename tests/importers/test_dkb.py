"""Tests for DKB CSV importer."""

import unittest
from os import path
from decimal import Decimal

from beancount.core import data
from beancount_toolbox.importers.dkb import DKBImporter
from beancount_toolbox.importers import Categorizer  # From parent importers.py module


def fixture_path(filename):
    """Get path to test fixture file."""
    return path.join(
        path.dirname(__file__),
        '..',
        'fixtures',
        filename,
    )


class TestDKBImporter(unittest.TestCase):
    """Test cases for DKB importer."""

    def setUp(self):
        """Set up test importer instance."""
        self.importer = DKBImporter(account='Assets:Current:Bank:DKB')
        self.sample_file = fixture_path('dkb_sample.csv')
        self.updated_file = fixture_path('dkb_updated.csv')

    def test_identify_valid_dkb_file(self):
        """Test that valid DKB CSV files are identified correctly."""
        self.assertTrue(self.importer.identify(self.sample_file))

    def test_identify_invalid_file(self):
        """Test that non-DKB files are not identified."""
        # Test with non-CSV file
        self.assertFalse(self.importer.identify('/path/to/file.txt'))

        # Test with non-existent file
        self.assertFalse(self.importer.identify('/path/to/nonexistent.csv'))

    def test_extract_transactions(self):
        """Test that transactions are extracted correctly."""
        entries = self.importer.extract(self.sample_file)

        # Should extract 5 transactions from sample file
        transactions = [e for e in entries if isinstance(e, data.Transaction)]
        self.assertEqual(len(transactions), 5)

    def test_date_parsing(self):
        """Test that German date format (dd.mm.yy) is parsed correctly."""
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # Check first transaction date (24.10.25 -> 2025-10-24)
        self.assertEqual(transactions[0].date.year, 2025)
        self.assertEqual(transactions[0].date.month, 10)
        self.assertEqual(transactions[0].date.day, 24)

    def test_amount_parsing_german_decimal(self):
        """Test that German decimal format (comma separator) is parsed correctly."""
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # First transaction: -19,99 EUR -> -19.99
        first_txn = transactions[0]
        bank_posting = [p for p in first_txn.postings
                       if p.account == 'Assets:Current:Bank:DKB'][0]
        self.assertEqual(bank_posting.units.number, Decimal('-19.99'))
        self.assertEqual(bank_posting.units.currency, 'EUR')

    def test_payee_and_narration(self):
        """Test that payee and narration are extracted correctly."""
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # First transaction
        self.assertEqual(transactions[0].payee, 'Telekom Shop GmbH')
        self.assertEqual(transactions[0].narration, 'Mobilfunkrechnung Oktober 2025')

    def test_link_from_kundenreferenz(self):
        """Test that Kundenreferenz is used as transaction link."""
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # First transaction has link REF12345
        self.assertIn('REF12345', transactions[0].links)

        # Third transaction has no Kundenreferenz (empty), so no links
        self.assertEqual(len(transactions[2].links), 0)

    def test_income_vs_expense_transactions(self):
        """Test that both income and expense transactions are handled."""
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # Transaction 0-2 are expenses (negative amounts)
        for i in range(3):
            bank_posting = [p for p in transactions[i].postings
                           if p.account == 'Assets:Current:Bank:DKB'][0]
            self.assertLess(bank_posting.units.number, 0)

        # Transactions 3-4 are income (positive amounts)
        for i in range(3, 5):
            bank_posting = [p for p in transactions[i].postings
                           if p.account == 'Assets:Current:Bank:DKB'][0]
            self.assertGreater(bank_posting.units.number, 0)

    def test_account_assignment(self):
        """Test that the account name is correctly assigned."""
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # All transactions should have a posting to the DKB account
        for txn in transactions:
            accounts = [p.account for p in txn.postings]
            self.assertIn('Assets:Current:Bank:DKB', accounts)

    def test_metadata_columns(self):
        """Test that metadata columns are stored."""
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # First transaction should have columns metadata
        # (Only if categorizer with column_map is configured)
        # For now, just check that meta exists
        self.assertIsNotNone(transactions[0].meta)

    def test_deduplication_same_file(self):
        """Test that importing same file twice produces no duplicates."""
        # First extraction
        entries1 = self.importer.extract(self.sample_file)

        transactions1 = [e for e in entries1 if isinstance(e, data.Transaction)]
        self.assertEqual(len(transactions1), 5)

        # Second extraction with same file
        entries2 = self.importer.extract(self.sample_file, existing=entries1)

        # Call deduplicate
        self.importer.deduplicate(entries2, entries1)

        # Check for duplicates
        transactions2 = [e for e in entries2 if isinstance(e, data.Transaction)]
        non_duplicates = [e for e in transactions2 if not e.meta.get('__duplicate__')]

        # All should be marked as duplicates
        self.assertEqual(len(non_duplicates), 0)

    def test_deduplication_updated_file(self):
        """Test that updated file with new transactions extracts only new ones."""
        # First extraction from sample file (5 transactions)
        entries1 = self.importer.extract(self.sample_file)

        transactions1 = [e for e in entries1 if isinstance(e, data.Transaction)]
        self.assertEqual(len(transactions1), 5)

        # Second extraction from updated file (7 transactions: 5 old + 2 new)
        entries2 = self.importer.extract(self.updated_file, existing=entries1)

        # Call deduplicate
        self.importer.deduplicate(entries2, entries1)

        # Check that only new transactions remain
        transactions2 = [e for e in entries2 if isinstance(e, data.Transaction)]
        non_duplicates = [e for e in transactions2 if not e.meta.get('__duplicate__')]

        # Should have 2 new transactions
        self.assertEqual(len(non_duplicates), 2)

        # Verify the new transactions are the ones from November
        dates = [txn.date for txn in non_duplicates]
        self.assertTrue(all(d.month == 11 for d in dates))

    def test_deduplication_with_unedited_transactions(self):
        """Test that unchanged transactions are detected as duplicates."""
        # First extraction
        entries1 = self.importer.extract(self.sample_file)

        # Keep all transactions unchanged (simulating a second import without user edits)
        # Second extraction from same file
        entries2 = self.importer.extract(self.sample_file, existing=entries1)

        # Call deduplicate
        self.importer.deduplicate(entries2, entries1)

        # All should be duplicates since nothing changed
        transactions2 = [e for e in entries2 if isinstance(e, data.Transaction)]
        non_duplicates = [e for e in transactions2 if not e.meta.get('__duplicate__')]

        # No new transactions (all marked as duplicates)
        self.assertEqual(len(non_duplicates), 0)

    def test_special_characters_in_narration(self):
        """Test that special characters (umlauts, quotes) are handled correctly."""
        # Note: Our test data uses standard German characters
        # The importer should handle them without issues due to UTF-8 encoding
        entries = self.importer.extract(self.sample_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        # Just verify that all transactions were extracted without encoding errors
        self.assertEqual(len(transactions), 5)

        # All narrations should be non-empty strings
        for txn in transactions:
            self.assertIsInstance(txn.narration, str)
            self.assertGreater(len(txn.narration), 0)


class TestDKBImporterWithCategorizer(unittest.TestCase):
    """Test cases for DKB importer with categorizer and regex capture groups."""

    def setUp(self):
        """Set up test importer instance with categorizer."""
        # Create categorization rules with regex capture groups
        # This matches the user's complex use case for mortgage payments
        rules = [
            {
                'match_payee': '^Commerzbank AG$',
                'match_narration': (
                    r'^DARLEHEN.+IBAN DE\d{2}XXXXXXXXX(?P<account_suffix>\d{4}).+'
                    r'Tilgung (?P<m_digits>\d+),(?P<m_frac>\d{2})\s+'
                    r'Zinsen (?P<i_digits>\d+),(?P<i_frac>\d{2})'
                ),
                'sub_account': 'RealEstate',
                'postings': [
                    {
                        'account': 'Liabilities:Bank:Mortgage:CoBa:{account_suffix}',
                        'amount': '{m_digits}.{m_frac} EUR',
                    },
                    {
                        'account': 'Expenses:Financial:Interest:Mortgage',
                        'amount': '{i_digits}.{i_frac} EUR',
                    },
                ],
            },
        ]

        categorizer = Categorizer(rules)
        self.importer = DKBImporter(
            account='Assets:Current:Bank:DKB',
            categorizer=categorizer,
        )
        self.mortgage_file = fixture_path('dkb_mortgage.csv')

    def test_categorizer_regex_capture_groups(self):
        """Test that categorizer extracts amounts from narration using regex capture groups."""
        entries = self.importer.extract(self.mortgage_file)

        transactions = [e for e in entries if isinstance(e, data.Transaction)]
        self.assertEqual(len(transactions), 1)

        txn = transactions[0]

        # Check payee and narration
        self.assertEqual(txn.payee, 'Commerzbank AG')
        self.assertIn('DARLEHEN', txn.narration)
        self.assertIn('Tilgung 450,00', txn.narration)
        self.assertIn('Zinsen 123,45', txn.narration)

        # Check that we have 3 postings (bank + principal + interest)
        self.assertEqual(len(txn.postings), 3)

        # Find each posting by account
        bank_posting = next(p for p in txn.postings
                           if 'Assets:Current:Bank:DKB' in p.account)
        principal_posting = next(p for p in txn.postings
                                if 'Liabilities:Bank:Mortgage' in p.account)
        interest_posting = next(p for p in txn.postings
                               if 'Expenses:Financial:Interest' in p.account)

        # Check bank posting (with sub_account)
        self.assertEqual(bank_posting.account, 'Assets:Current:Bank:DKB:RealEstate')
        self.assertEqual(bank_posting.units.number, Decimal('-573.45'))
        self.assertEqual(bank_posting.units.currency, 'EUR')

        # Check principal posting (extracted from narration)
        self.assertEqual(principal_posting.account, 'Liabilities:Bank:Mortgage:CoBa:6789')
        self.assertEqual(principal_posting.units.number, Decimal('450.00'))
        self.assertEqual(principal_posting.units.currency, 'EUR')

        # Check interest posting (extracted from narration)
        self.assertEqual(interest_posting.account, 'Expenses:Financial:Interest:Mortgage')
        self.assertEqual(interest_posting.units.number, Decimal('123.45'))
        self.assertEqual(interest_posting.units.currency, 'EUR')

        # Verify the amounts balance correctly
        total = sum(p.units.number for p in txn.postings)
        self.assertEqual(total, Decimal('0'))

    def test_categorizer_account_suffix_substitution(self):
        """Test that account suffix from regex capture group is correctly substituted."""
        entries = self.importer.extract(self.mortgage_file)
        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        txn = transactions[0]
        principal_posting = next(p for p in txn.postings
                                if 'Liabilities:Bank:Mortgage' in p.account)

        # The account suffix '6789' should be extracted from the IBAN in narration
        self.assertIn('6789', principal_posting.account)
        self.assertEqual(principal_posting.account, 'Liabilities:Bank:Mortgage:CoBa:6789')

    def test_categorizer_sub_account(self):
        """Test that sub_account is correctly appended to bank account."""
        entries = self.importer.extract(self.mortgage_file)
        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        txn = transactions[0]
        bank_posting = next(p for p in txn.postings
                           if 'Assets:Current:Bank:DKB' in p.account)

        # The sub_account 'RealEstate' should be appended to the bank account
        self.assertEqual(bank_posting.account, 'Assets:Current:Bank:DKB:RealEstate')


if __name__ == '__main__':
    unittest.main()
