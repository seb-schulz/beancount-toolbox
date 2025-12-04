"""Categorizer for automatic transaction categorization."""

import re

import yaml
from beancount.core import data


USLESS_LINKS = {'NOTPROVIDED'}


class Categorizer(object):
    """Automatic transaction categorizer using YAML rule definitions.

    The Categorizer applies pattern-matching rules to transactions to automatically
    assign expense/income accounts and add additional postings.

    Example usage:
        categorizer = Categorizer.from_yaml_file('rules.yaml')
        importer = DKBImporter(account='Assets:Bank:DKB', categorizer=categorizer)
    """

    @classmethod
    def from_yaml_file(cls, filename, **kwargs):
        """Load categorization rules from a YAML file.

        Args:
            filename: Path to YAML file containing rules
            **kwargs: Additional arguments passed to Categorizer constructor

        Returns:
            Categorizer instance with loaded rules
        """
        with open(filename) as fp:
            return cls(yaml.safe_load(fp), **kwargs)

    def __init__(self, rules) -> None:
        """Initialize categorizer with rules.

        Args:
            rules: List of rule dictionaries from YAML
        """
        self.rules = rules
        self.column_map = {}

    def normalize_transaction(self, txn, row):
        """Hook for custom transaction normalization.

        Override this method in subclasses to apply custom transformations.

        Args:
            txn: Transaction to normalize
            row: Raw CSV row data

        Returns:
            Normalized transaction
        """
        return txn

    def __call__(self, txn, row):
        """Apply categorization rules to a transaction.

        Args:
            txn: Transaction directive to categorize
            row: Raw CSV row data (list or tuple)

        Returns:
            Modified transaction with categorization applied
        """
        if len(USLESS_LINKS & txn.links) > 0:
            txn = txn._replace(links=txn.links - USLESS_LINKS)

        if txn.date == txn.meta.get('date', None):
            del txn.meta['date']

        txn = self.normalize_transaction(txn, row)

        def sanitize_row(x):
            return re.sub(r'\s\s+', ' ', x, re.MULTILINE).strip()

        if len(self.column_map) > 0:
            txn.meta['columns'] = ''.join([
                '{',
                ','.join(f"{col!r}:{sanitize_row(row[idx])!r}"
                         for col, idx in self.column_map.items()
                         if len(row[idx]) > 0),
                '}',
            ])

        def re_search(matches, pattern: str, text):
            if pattern is None:
                return 0

            g = re.search(pattern.strip(), text, re.IGNORECASE)
            if g:
                matches.append(g.groupdict())
            return 1

        for rule in self.rules:
            required_matches = 0
            matches = []
            required_matches += re_search(matches, rule.get('match_payee'),
                                          txn.payee)
            required_matches += re_search(matches, rule.get('match_narration'),
                                          txn.narration)

            if len(matches) < required_matches:
                continue

            context = {'amount_credit': str(-txn.postings[0].units)}
            for g in matches:
                context.update(**g)

            if 'sub_account' in rule:
                txn.postings[0] = txn.postings[0]._replace(
                    account='{}:{}'.format(
                        txn.postings[0].account,
                        rule['sub_account'],
                    ))
            try:
                for p in rule['postings']:
                    account = p['account'].format(**context)

                    if 'amount' in p:
                        amount = data.Amount.from_string(
                            p['amount'].format(**context))
                    else:
                        init_unit: data.Amount = txn.postings[0].units
                        amount = data.Amount(-init_unit.number,
                                             init_unit.currency)

                    txn.postings.append(
                        data.Posting(account, amount, None, None, None, None))
            except KeyError:
                pass
            return txn
        return txn
