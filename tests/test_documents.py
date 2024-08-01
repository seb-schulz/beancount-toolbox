import unittest

from beancount import loader


class TestDocuments(unittest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_valid_beanfile(self, _, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))

    @loader.load_doc()
    def test_valid_document_entries(self, entries, errors, __):
        """
        plugin "beancount_toolbox.plugins.documents"

        2011-01-01 open Expenses:Food
        2011-01-01 open Assets:Other

        2011-05-17 * "Something" #tag
            invoice: "pyproject.toml"
            Expenses:Food         1.00 USD
            Assets:Other         -1.00 USD
        """
        self.assertEqual(0, len(errors))
        self.assertEqual(5, len(entries))


if __name__ == '__main__':
    unittest.main()
