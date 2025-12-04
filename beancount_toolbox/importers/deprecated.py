"""Deprecated functionality with migration guidance.

This module contains stubs for removed classes and functions that raise
ImportError with helpful migration messages to guide users to the correct
replacements.
"""


def custom_excel(*args, **kwargs):
    """Deprecated: custom_excel has been removed."""
    raise ImportError(
        "custom_excel has been removed. "
        "Use csv.excel with a custom delimiter instead. "
        "Example: class MyDialect(csv.excel): delimiter = ';'"
    )


def _get_header_dict(*args, **kwargs):
    """Deprecated: Internal function removed."""
    raise ImportError(
        "_get_header_dict() has been removed. "
        "This was an internal function and is not part of the public API."
    )


def CSVImporter(*args, **kwargs):
    """Deprecated: CSVImporter has been removed."""
    raise ImportError(
        "CSVImporter has been removed. "
        "Please use beangulp.importers.csvbase.Importer directly "
        "or create a custom importer like DKBImporter. "
        "See beancount_toolbox.importers.dkb.DKBImporter and examples/import.py for reference."
    )


def keep_similar_old_entries(*args, **kwargs):
    """Deprecated: Function removed in favor of beangulp deduplication."""
    raise ImportError(
        "keep_similar_old_entries() has been removed. "
        "Use beangulp's built-in deduplication mechanism instead. "
        "Pass the -e flag with your existing beancount file: "
        "python import.py extract imports/ -e main.bean"
    )


def MobileFinanceImporter(*args, **kwargs):
    """Deprecated: MobileFinanceImporter has been removed."""
    raise ImportError(
        "MobileFinanceImporter has been removed. "
        "Create a custom importer extending beangulp.importer.ImporterProtocol. "
        "See beangulp documentation for migration guidance."
    )


def hash_entry(*args, **kwargs):
    """Deprecated: hash_entry has been removed."""
    raise ImportError(
        "hash_entry() has been removed. "
        "Use beancount.core.compare.hash_entry() instead for similar functionality."
    )


def dedect_duplicates(*args, **kwargs):
    """Deprecated: Function removed in favor of beangulp deduplication."""
    raise ImportError(
        "dedect_duplicates() has been removed. "
        "Use beangulp's built-in deduplication mechanism instead. "
        "Pass the -e flag with your existing beancount file: "
        "python import.py extract imports/ -e main.bean"
    )


def ingest(*args, **kwargs):
    """Deprecated: Wrapper function removed."""
    raise ImportError(
        "ingest() has been removed. "
        "Use beangulp.Ingest() directly or scripts_utils.ingest(). "
        "See examples/import.py for the recommended pattern."
    )
