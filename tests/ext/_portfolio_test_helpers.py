"""Test helpers for portfolio monitor tests.

Provides custom decorator for integration tests.
"""
from __future__ import annotations

import functools
import io
import os
import tempfile
import textwrap
from typing import Callable

from beancount import loader
from beancount.parser import printer
from fava.context import g
from fava.core import FavaLedger
from flask import Flask

from beancount_toolbox.ext.portfolio_monitor import Portfolio, portfolio


def load_portfolio(
    root_account: str | None = None,
    time_filter: str | None = None,
) -> Callable:
    """Decorator that loads beancount doc from test docstring and runs portfolio extension.

    Extracts beancount data from test docstring, validates it, sets up Fava/Flask context,
    runs the portfolio extension, and passes the Portfolio result to the test function.

    Args:
        root_account: Root account for portfolio (overrides class attribute if provided)
        time_filter: Time filter string like "2020-01-01 to 2020-12-31" (overrides class attribute)

    Returns:
        Decorator function that wraps the test

    Example:
        >>> class MyTest(PortfolioTestCase):
        ...     root_account = "Assets:Investments"
        ...
        ...     @load_portfolio(time_filter="2020-01-01 to 2020-12-31")
        ...     def test_example(self, result: Portfolio):
        ...         '''
        ...         option "operating_currency" "USD"
        ...         2020-01-01 open Assets:Investments:Stock STOCK
        ...         '''
        ...         self.assertIsInstance(result, Portfolio)
    """
    def decorator(test_fn: Callable) -> Callable:
        @functools.wraps(test_fn)
        def wrapper(self, *args, **kwargs):
            # Extract beancount data from docstring
            doc = test_fn.__doc__
            if not doc:
                raise ValueError(
                    f"{test_fn.__name__} requires a docstring with beancount data")

            # Validate beancount syntax (fail fast on errors)
            bean_data = textwrap.dedent(doc).strip()
            entries, errors, options_map = loader.load_string(
                bean_data, dedent=True)

            if errors:
                # Fail test with error details (like @loader.load_doc expect_errors=False)
                oss = io.StringIO()
                printer.print_errors(errors, file=oss)
                self.fail(
                    f"Beancount parsing errors in {test_fn.__name__}:\n{oss.getvalue()}")

            # Get parameters (decorator args override class attributes)
            _root_account = root_account if root_account is not None else getattr(
                self, 'root_account', 'Assets')
            _time_filter = time_filter if time_filter is not None else getattr(
                self, 'time_filter', None)

            # Run portfolio extension
            result = _run_portfolio_extension(doc, _root_account, _time_filter)

            # Call test with Portfolio result (no return to avoid deprecation warning)
            test_fn(self, result)

        return wrapper
    return decorator


def _run_portfolio_extension(
    doc: str,
    root_account: str,
    time_filter: str | None = None
) -> Portfolio:
    """Helper to run portfolio extension with given beancount doc.

    Creates a temporary .bean file, initializes FavaLedger, sets up Flask app context,
    applies optional time filtering, and runs the portfolio extension.

    Args:
        doc: Beancount document string (directives)
        root_account: Root account for portfolio
        time_filter: Optional time filter string like "2020-01-01 to 2020-12-31"

    Returns:
        Portfolio result from extension
    """
    bean_data = textwrap.dedent(doc).strip() + "\n"

    with tempfile.NamedTemporaryFile("w", suffix=".bean", delete=False) as handle:
        handle.write(bean_data)
        path = handle.name

    try:
        ledger = FavaLedger(path)
        app = Flask(__name__)
        with app.app_context():
            if time_filter:
                filtered = ledger.get_filtered(time=time_filter)
            else:
                filtered = ledger.get_filtered()
            g.ledger = ledger
            g.filtered = filtered

            return portfolio(
                {"root_account": root_account}, None
            )  # pyright: ignore[reportReturnType]
    finally:
        os.remove(path)
