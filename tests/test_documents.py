import unittest

from os import path
from beancount import loader
from beancount_toolbox.plugins import documents


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
