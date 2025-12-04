"""DKB (Deutsche Kreditbank) CSV Importer for beangulp.

This importer handles DKB bank CSV exports with the following characteristics:
- UTF-8 BOM encoded, semicolon-separated values
- 4 header lines before column names
- German date format (dd.mm.yy)
- German decimal format (comma separator)
- 12 columns including IBAN, reference numbers, and transaction details

Usage:
    ```python
    #!/usr/bin/env python3
    import beangulp
    from beancount_toolbox.importers.dkb import DKBImporter
    from beancount_toolbox.importers import Categorizer

    categorizer = Categorizer.from_yaml_file('rules.yaml', iban=7)

    CONFIG = [
        DKBImporter(
            account='Assets:Current:Bank:DKB',
            categorizer=categorizer,
        ),
    ]

    if __name__ == '__main__':
        ingest = beangulp.Ingest(CONFIG)
        ingest()
    ```

Deduplication:
    This importer relies on beangulp's built-in deduplication mechanism.
    Running extraction multiple times on the same data will not create duplicates.
    User-edited transactions (e.g., corrected expense accounts) are preserved
    when re-importing.
"""

import csv
import re
from typing import Any, Optional

from beancount.core import data
from beangulp.importers.csvbase import Amount, Column, Date, Importer, Order


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text fields.

    Replaces multiple consecutive whitespace characters (spaces, tabs, newlines)
    with a single space and strips leading/trailing whitespace.

    Args:
        text: Input text to normalize

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return text
    return re.sub(r'\s+', ' ', text.strip())


class NormalizedColumn(Column):
    """Column that normalizes whitespace in the value."""

    def parse(self, value):
        return _normalize_whitespace(value)


class DKBImporter(Importer):
    """Importer for DKB bank CSV exports."""

    # CSV file format configuration
    encoding = 'utf-8-sig'  # Handle UTF-8 BOM
    skiplines = 5  # Skip 5 metadata/empty lines before column names
    order = None  # Let csvbase auto-detect and normalize to ascending order

    date = Date('Buchungsdatum', frmt='%d.%m.%y')  # type: ignore[assignment]
    amount = Amount('Betrag (€)', subs={r'\.': '', r',': '.'})
    payee = NormalizedColumn('Zahlungsempfänger*in')
    narration = NormalizedColumn('Verwendungszweck')
    link = Column('Kundenreferenz')

    def __init__(self, account: str, categorizer: Optional[Any] = None):
        """Initialize DKB importer.

        Args:
            account: Beancount account name for the bank account (e.g., 'Assets:Current:Bank:DKB')
            categorizer: Optional Categorizer instance for automatic transaction categorization
        """
        super().__init__(account=account, currency='EUR', flag='*')
        self.categorizer = categorizer

        # Create custom CSV dialect for DKB (semicolon-separated)
        class DKBDialect(csv.excel):
            delimiter = ';'
        self.dialect = DKBDialect

    @property
    def name(self) -> str:
        """Return importer name."""
        return 'DKB'

    def extract(self, filepath: str, existing: Optional[data.Entries] = None) -> data.Entries:
        """Extract transactions from the DKB CSV file.

        Args:
            filepath: Path to the CSV file
            existing: Existing entries for deduplication

        Returns:
            List of extracted transaction directives (in original CSV order)
        """
        if existing is None:
            existing = []

        entries = super().extract(filepath, existing)
        if self.order == Order.DESCENDING:
            entries.reverse()

        return entries

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

    def metadata(self, filepath: str, lineno: int, row) -> dict:
        """Build transaction metadata dictionary with all CSV columns.

        Args:
            filepath: Path to the file being imported
            lineno: Line number of the data being processed
            row: The data row being processed (tuple of CSV values)

        Returns:
            A metadata dictionary
        """
        meta = data.new_metadata(filepath, lineno)

        # Build columns metadata with all non-empty fields from the raw row
        # The row is a tuple, so we need to get the original CSV column names
        # We'll reconstruct this from the raw tuple data
        if len(row) >= 12:  # DKB has 12 columns
            column_names = [
                'Buchungsdatum', 'Wertstellung', 'Status', 'Zahlungspflichtige*r',
                'Zahlungsempfänger*in', 'Verwendungszweck', 'Umsatztyp', 'IBAN',
                'Betrag (€)', 'Gläubiger-ID', 'Mandatsreferenz', 'Kundenreferenz'
            ]

            columns_data = {}
            for col_name, col_value in zip(column_names, row):
                if col_value and col_value.strip():
                    columns_data[col_name] = _normalize_whitespace(col_value)

            if columns_data:
                meta['columns'] = str(columns_data)

        return meta

    def finalize(self, txn: data.Transaction, row) -> Optional[data.Transaction]:
        """Post-process the transaction to add categorizer support and fix link format.

        Args:
            txn: The just-built Transaction object
            row: The data row being processed

        Returns:
            A potentially extended or modified Transaction object or None
        """
        # Clean up link (remove spaces) and only include if non-empty
        link_value = row.link.strip() if hasattr(row, 'link') and row.link else ''
        links = {link_value.replace(' ', '')} if link_value else set()

        # Create placeholder posting for expense/income account
        placeholder_posting = data.Posting(
            account='Expenses:FIXME',
            units=None,  # Auto-balanced
            cost=None,
            price=None,
            flag=None,
            meta={},
        )

        # Update transaction with cleaned links and placeholder posting
        # Note: payee is already set from the 'payee' column (Zahlungsempfänger*in)
        txn = txn._replace(
            links=links,
            postings=list(txn.postings) + [placeholder_posting]
        )

        # Apply categorizer if configured
        if self.categorizer:
            # Convert row tuple to list for categorizer compatibility
            row_list = list(row)
            txn = self.categorizer(txn, row_list)

            # Remove the placeholder posting if categorizer added real postings
            if len(txn.postings) > 2:
                txn = txn._replace(
                    postings=[p for p in txn.postings if p.account !=
                              'Expenses:FIXME']
                )

        return txn
