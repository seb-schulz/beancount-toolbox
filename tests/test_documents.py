import unittest

from os import path
from beancount import loader
from beancount.core import data
from beancount_toolbox.plugins import documents
import datetime


class TestDocuments(unittest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_valid_beanfile(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(3, len(entries))

    @loader.load_doc(expect_errors=True)
    def test_valid_invoice_entries_strict(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents" "strict"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            invoice: "invoice.pdf"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(1, len(errors))
        self.assertEqual(3, len(entries))
        self.assertTrue(errors[0].message.startswith('missing file'))

    @loader.load_doc()
    def test_valid_invoice_entries(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            invoice: "invoice.pdf"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(5, len(entries))

    @loader.load_doc()
    def test_valid_document_entries(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            document: "pyproject.toml"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(5, len(entries))

    @loader.load_doc()
    def test_valid_document_entries(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            document: "pyproject.toml"
            Expenses:Food         2.00 USD
            Assets:Other         -1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(5, len(entries))

    @loader.load_doc()
    def test_valid_document_entries(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            document: "pyproject.toml"
            Expenses:Food         2.00 USD
            Assets:Other         -2.00 USD
        """
        self.assertEqual(0, len(errors))
        dates = [x.date for x in entries if isinstance(x, data.Document)]
        self.assertListEqual(
            [datetime.date(2011, 5, 17),
             datetime.date(2011, 5, 17)],
            dates,
        )

    @loader.load_doc()
    def test_valid_document_entries(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            document: "2011-05-15.pyproject.toml"
            Expenses:Food         2.00 USD
            Assets:Other         -2.00 USD
        """
        self.assertEqual(0, len(errors))
        dates = [x.date for x in entries if isinstance(x, data.Document)]
        self.assertListEqual(
            [datetime.date(2011, 5, 15),
             datetime.date(2011, 5, 15)],
            dates,
        )

    @loader.load_doc()
    def test_check_file_path(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            document: "bean-check"
            Expenses:Food         2.00 USD
            Assets:Other         -2.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertTrue(
            all([
                x.filename.endswith('venv/bin/bean-check') for x in entries
                if isinstance(x, data.Document)
            ]))


class TestBasePathFromConfig(unittest.TestCase):

    def test_none_values(self):
        got = documents._basepath_from_config()
        self.assertEqual(got, path.dirname(path.dirname(__file__)))

    def test_with_option_map_filename(self):
        pass

    def test_relative_config_path(self):
        pass

    def test_abs_config_path(self):
        pass


if __name__ == '__main__':
    unittest.main()
