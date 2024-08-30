import os
import unittest

from os import path
from beancount import loader
from beancount.core import data
from beancount_toolbox.plugins import documents
import datetime


def fixture_path() -> str:
    return path.join(
        path.dirname(path.dirname(__file__)),
        'fixtures',
        'documents',
    )


class TestDocuments(unittest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_valid_beanfile(self, entries, errors, options_map):
        """
        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        from beancount_toolbox.plugins.documents import documents
        entries, errors = documents(entries, options_map, None)

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
    def test_check_file_path(self, entries, errors, options_map):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            document: "c.txt"
            Expenses:Food         2.00 USD
            Assets:Other         -2.00 USD
        """
        raise
        self.assertEqual(0, len(errors))
        from beancount_toolbox.plugins.documents import documents
        entries, errors = documents(entries, options_map, fixture_path())

        self.assertEqual(0, len(errors))
        self.assertTrue(
            all([
                x.filename.endswith('b/c.txt') for x in entries
                if isinstance(x, data.Document)
            ]))


class TestBasePathFromConfig(unittest.TestCase):

    def test_none_values(self):
        got = documents._basepath_from_config()
        self.assertEqual(
            got,
            path.join(os.getcwd(), 'documents'),
        )

    def test_with_option_map_filename(self):
        got = documents._basepath_from_config(
            {'filename': path.join(fixture_path(), 'empty.bean')})
        self.assertEqual(got, path.join(fixture_path(), 'documents'))

    def test_relative_config_path(self):
        self.assertEqual(
            documents._basepath_from_config({}, 'foobar'),
            path.join(os.getcwd(), 'foobar'),
        )
        self.assertEqual(
            documents._basepath_from_config(
                {
                    'filename': path.join(fixture_path(), 'empty.bean'),
                },
                'foobar',
            ),
            path.join(fixture_path(), 'foobar'),
        )

    def test_abs_config_path(self):
        self.assertEqual(
            documents._basepath_from_config({}, fixture_path()),
            fixture_path(),
        )
        self.assertEqual(
            documents._basepath_from_config(
                {
                    'filename': path.join(fixture_path(), 'empty.bean'),
                },
                fixture_path(),
            ),
            fixture_path(),
        )


if __name__ == '__main__':
    unittest.main()
