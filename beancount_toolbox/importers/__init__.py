"""Importers package for beancount-toolbox.

This package contains various importers for different financial institutions
and the Categorizer utility for automatic transaction categorization.
"""

# Active imports
from beancount_toolbox.importers.categorizer import Categorizer
from beancount_toolbox.importers.dkb import DKBImporter

# Deprecated imports (raise ImportError with migration guidance)
from beancount_toolbox.importers.deprecated import (
    CSVImporter,
    MobileFinanceImporter,
    custom_excel,
    dedect_duplicates,
    hash_entry,
    ingest,
    keep_similar_old_entries,
)

__all__ = [
    # Active exports
    'Categorizer',
    'DKBImporter',
    # Deprecated exports (raise ImportError with migration guidance)
    'CSVImporter',
    'MobileFinanceImporter',
    'custom_excel',
    'dedect_duplicates',
    'hash_entry',
    'ingest',
    'keep_similar_old_entries',
]
