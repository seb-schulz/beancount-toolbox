"""Importers package for beancount-toolbox.

This package contains various importers for different financial institutions.
"""

import importlib.util
import sys
from pathlib import Path

# Import specific bank importers
from beancount_toolbox.importers.dkb import DKBImporter

# Re-export Categorizer from parent importers.py module
# Note: This works around the naming conflict between importers.py and importers/

# Temporarily add parent directory to path to import from importers.py
parent_path = str(Path(__file__).parent.parent)
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

# Import the legacy Categorizer from beancount_toolbox.importers module (importers.py file)
spec = importlib.util.spec_from_file_location(
    "beancount_toolbox_importers_legacy",
    Path(__file__).parent.parent / "importers.py"
)
if spec and spec.loader:
    importers_legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importers_legacy)
    Categorizer = importers_legacy.Categorizer
else:
    raise ImportError("Could not load Categorizer from importers.py")

__all__ = [
    'DKBImporter',
    'Categorizer',
]
