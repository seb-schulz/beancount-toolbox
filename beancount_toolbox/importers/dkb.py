"""DKB (Deutsche Kreditbank) CSV Importer for beangulp.

This importer handles DKB bank CSV exports with the following characteristics:
- UTF-8 BOM encoded, semicolon-separated values
- 4 header lines before column names
- German date format (dd.mm.yy)
- German decimal format (comma separator)
- 12 columns including IBAN, reference numbers, and transaction details

Usage:
    from beancount_toolbox.importers.dkb import DKBImporter

    # Create importer
    importer = DKBImporter(account='Assets:Current:Bank:DKB')

    # Use with beangulp
    # beangulp identify imports/
    # beangulp extract imports/ -e existing.bean

Deduplication:
    This importer relies on beangulp's built-in deduplication mechanism.
    Running extraction multiple times on the same data will not create duplicates.
    User-edited transactions (e.g., corrected expense accounts) are preserved
    when re-importing.
"""

import csv
import datetime
from decimal import Decimal
from typing import Any, Optional

from beancount.core import data, amount
from beangulp import Importer


class DKBImporter(Importer):
    """Importer for DKB bank CSV exports."""

    def __init__(self, account: str, categorizer: Optional[Any] = None):
        """Initialize DKB importer.

        Args:
            account: Beancount account name for the bank account (e.g., 'Assets:Current:Bank:DKB')
            categorizer: Optional Categorizer instance for automatic transaction categorization
        """
        self._account = account
        self.categorizer = categorizer

    @property
    def name(self) -> str:
        """Return importer name."""
        return 'DKB'

    def identify(self, filepath: str) -> bool:
        """Identify DKB CSV files by checking for specific header structure.

        Args:
            filepath: Path to the file to identify

        Returns:
            True if the file appears to be a DKB CSV export, False otherwise
        """
        if not filepath.endswith('.csv'):
            return False

        try:
            with open(filepath, encoding='utf-8-sig') as f:
                # Read first 10 lines to check headers
                lines = [f.readline() for _ in range(10)]
                content = ''.join(lines)

            # Check for DKB-specific markers in the header
            return (
                'Girokonto' in content and
                'Buchungsdatum' in content and
                'Betrag (€)' in content and
                'Zahlungsempfänger*in' in content
            )
        except (IOError, UnicodeDecodeError):
            return False

    def account(self, filepath: str) -> str:
        """Return the account for transactions from this file.

        Args:
            filepath: Path to the file

        Returns:
            Account name
        """
        return self._account

    def extract(self, filepath: str, existing: Optional[data.Entries] = None) -> data.Entries:
        """Extract transactions from the DKB CSV file.

        Args:
            filepath: Path to the CSV file
            existing: Existing entries for deduplication

        Returns:
            List of extracted transaction directives
        """
        entries = []

        with open(filepath, encoding='utf-8-sig') as f:
            # Skip the 5 header lines (including empty line after metadata)
            for _ in range(5):
                f.readline()

            # Now read the CSV data
            reader = csv.DictReader(f, delimiter=';', quotechar='"')

            # Store column names for categorizer
            fieldnames = None

            for row_dict in reader:
                # Store fieldnames from first row
                if fieldnames is None:
                    fieldnames = list(reader.fieldnames) if reader.fieldnames else []

                # Convert DictReader row to list for categorizer compatibility
                row = [row_dict.get(field, '') for field in fieldnames]

                # Skip rows without required fields
                if not row_dict.get('Buchungsdatum') or not row_dict.get('Betrag (€)'):
                    continue

                # Parse date (dd.mm.yy format)
                date_str = row_dict['Buchungsdatum']
                day, month, year = date_str.split('.')
                # Assume 20xx for 2-digit years
                year_full = 2000 + int(year)
                txn_date = datetime.date(year_full, int(month), int(day))

                # Parse amount (German decimal format: -19,99)
                amount_str = row_dict['Betrag (€)']
                amount_decimal = Decimal(amount_str.replace('.', '').replace(',', '.'))

                # Get payee and narration
                payee = row_dict.get('Zahlungsempfänger*in', '').strip()
                narration = row_dict.get('Verwendungszweck', '').strip()

                # Get link from Kundenreferenz if available
                links = set()
                kundenreferenz = row_dict.get('Kundenreferenz', '').strip()
                if kundenreferenz:
                    links.add(kundenreferenz.replace(' ', ''))

                # Create metadata dict
                meta = {}

                # Build columns metadata with all non-empty fields
                columns_data = {}
                for col_name, col_value in row_dict.items():
                    if col_value and col_value.strip():
                        columns_data[col_name] = col_value.strip()

                if columns_data:
                    meta['columns'] = str(columns_data)

                # Create transaction with two postings
                # First posting: to the bank account (with amount from CSV)
                # Second posting: placeholder for expense/income (auto-balanced)
                txn = data.Transaction(
                    meta=meta,
                    date=txn_date,
                    flag='*',
                    payee=payee if payee else None,
                    narration=narration,
                    tags=set(),
                    links=links,
                    postings=[
                        data.Posting(
                            account=self._account,
                            units=amount.Amount(amount_decimal, 'EUR'),
                            cost=None,
                            price=None,
                            flag=None,
                            meta={},
                        ),
                        data.Posting(
                            account='Expenses:FIXME',  # Placeholder
                            units=None,  # Auto-balanced
                            cost=None,
                            price=None,
                            flag=None,
                            meta={},
                        ),
                    ],
                )

                # Apply categorizer if configured
                if self.categorizer:
                    txn = self.categorizer(txn, row)
                    # Remove the placeholder posting if categorizer added real postings
                    # Categorizer adds postings to the end, so if we have more than 2 postings,
                    # remove the second one (Expenses:FIXME placeholder)
                    if len(txn.postings) > 2:
                        # Filter out the placeholder posting
                        txn = txn._replace(
                            postings=[p for p in txn.postings if p.account != 'Expenses:FIXME']
                        )

                entries.append(txn)

        return entries
