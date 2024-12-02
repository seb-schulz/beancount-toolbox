import csv as pycsv
import hashlib
import io
import os
import re
import sys
import warnings
from os import path

import yaml
from beancount import loader
from beancount.core import compare, data, flags, getters, number
from beancount.ingest import importer, scripts_utils
from beancount.ingest.importers import csv


class custom_excel(pycsv.excel):
    delimiter = ';'


def _get_header_dict(config, head, dialect='excel', skip_lines: int = 0):
    """Using the header line, convert the configuration field name lookups to int indexes.

    Args:
      config: A dict of Col types to string or indexes.
      head: A string, some decent number of bytes of the head of the file.
      dialect: A dialect definition to parse the header
      skip_lines: Skip first x (garbage) lines of file.
    Returns:
      A pair of
        A dict of Col types to integer indexes of the fields, and
        a boolean, true if the file has a header.
    Raises:
      ValueError: If there is no header and the configuration does not consist
        entirely of integer indexes.
    """
    # Skip garbage lines before sniffing the header
    assert isinstance(skip_lines, int)
    assert skip_lines >= 0
    for _ in range(skip_lines):
        head = head[head.find('\n') + 1:]

    has_header = pycsv.Sniffer().has_header(head)
    if not has_header:
        return {}

    header = next(pycsv.reader(io.StringIO(head), dialect=dialect))
    field_map = {
        field_name.strip(): index
        for index, field_name in enumerate(header)
        if len(field_name.strip()) > 0 and field_name not in config.values()
    }
    return field_map


class CSVImporter(csv.Importer):

    def parse_amount(self, string):
        return number.D(string.replace('.', '').replace(',', '.'))

    def extract(self, file, *args, **kwargs):
        if 'column_map' in dir(self.categorizer):
            self.categorizer.column_map.update(
                _get_header_dict(
                    self.config,
                    file.head(encoding=self.encoding),
                    self.csv_dialect,
                    self.skip_lines,
                ))
        entries = super().extract(file, *args, **kwargs)
        for i in range(len(entries)):
            entry = entries[i]
            entries[i] = entry._replace(
                payee=re.sub(r'\s\s+', ' ', entry.payee, re.MULTILINE),
                links=set([x.replace(' ', '') for x in entry.links])
            )
        return entries


def keep_similar_old_entries(new_entries, old_entries):

    def gen_mapper(k):
        return dict([(
            e.meta[k], e
        ) for e in old_entries if k in e.meta and not any(
            map(lambda p: p.account == 'Expenses:Uncategorised', e.postings))])

    if old_entries is None:
        return new_entries

    old_entries_sha1v2 = gen_mapper('sha1v2')

    r = []
    for filename, entries in new_entries:
        xs = []
        for new_entry in entries:
            if 'sha1v2' in new_entry.meta:
                xs.append(
                    old_entries_sha1v2.get(new_entry.meta['sha1v2'],
                                           new_entry))
            else:
                xs.append(new_entry)
        r.append((filename, xs))
    return r


class MobileFinanceImporter(importer.ImporterProtocol):
    # A flag to use on new transaction. Override this flag in derived classes if
    # you prefer to create your imported transactions with a different flag.
    FLAG = flags.FLAG_WARNING

    def __init__(self, *, account_replacement={}):
        self.account_replacement = account_replacement

    def _remap_accounts(self, entries):
        ar = self.account_replacement
        for entry in entries:
            if isinstance(entry, data.Balance) and entry.account in ar.keys():
                yield entry._replace(account=ar[entry.account])
            elif isinstance(entry, data.Transaction) and any(
                    [p.account in ar.keys() for p in entry.postings]):
                yield entry._replace(postings=[
                    p._replace(account=ar.get(p.account, p.account))
                    for p in entry.postings
                ])
            else:
                yield entry

    def identify(self, file):
        return re.search(r'\.bean$', file.name) is not None

    def extract(self, file, existing_entries=None):
        entries, _errors, _options = loader.load_file(file.name)
        entries = list(self._remap_accounts(entries))

        if existing_entries is not None:
            open_close_entries = getters.get_account_open_close(
                existing_entries)
            entries = [
                entry for entry in entries if any([
                    isinstance(entry, data.Balance)
                    and entry.account in open_close_entries.keys(),
                    isinstance(entry, data.Transaction) and any([
                        p.account in open_close_entries.keys()
                        for p in entry.postings
                    ]),
                    not isinstance(entry, (data.Balance, data.Commodity,
                                           data.Open, data.Transaction)),
                ])
            ]

            existing_hashes = dict([(entry.meta['mobile_finance_hash'], entry)
                                    for entry in existing_entries
                                    if 'mobile_finance_hash' in entry.meta])
            entries = [
                existing_hashes.get(
                    compare.hash_entry(entry, exclude_meta=True),
                    entry._replace(
                        meta=dict(mobile_finance_hash=compare.hash_entry(
                            entry, exclude_meta=True),
                            **entry.meta))) for entry in entries
            ]

        return entries

    def file_date(self, file):
        """Attempt to obtain a date that corresponds to the given file.

        Args:
          file: A cache.FileMemo instance.
        Returns:
          A date object, if successful, or None if a date could not be extracted.
          (If no date is returned, the file creation time is used. This is the
          default.)
        """


USLESS_LINKS = {'NOTPROVIDED'}


class Categorizer(object):

    @classmethod
    def from_yaml_file(cls, filename, **kwargs):
        with open(filename) as fp:
            return cls(yaml.safe_load(fp), **kwargs)

    def __init__(self, rules, *, bic=None, iban=None, sha1v2=None) -> None:
        self.rules = rules
        self._bic, self._iban = bic, iban
        self._sha1v2 = sha1v2
        self.column_map = {}

    def __call__(self, txn, row):
        if len(USLESS_LINKS & txn.links) > 0:
            txn = txn._replace(links=txn.links - USLESS_LINKS)

        if txn.date == txn.meta.get('date', None):
            del txn.meta['date']

        if self._iban is not None:
            txn.meta['iban'] = row[self._iban]
        if self._bic is not None:
            txn.meta['bic'] = row[self._bic]

        if self._sha1v2 is not None:
            txn.meta['sha1v2'] = hashlib.sha1(''.join(
                [row[i] for i in self._sha1v2]).encode('utf-8')).hexdigest()

        if len(self.column_map) > 0:
            txn.meta['columns'] = ''.join([
                '{',
                ','.join(f"{col!r}:{row[idx].strip()!r}"
                         for col, idx in self.column_map.items()
                         if len(row[idx]) > 0 and idx not in (self._iban,
                                                              self._bic)),
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


def hash_entry(txn, meta_subset=[], debug=False):
    hashobj = hashlib.sha1()
    for attr_name, attr_value in zip(txn._fields, txn):
        if attr_name in ('postings', 'meta', 'tags'):
            continue

        if isinstance(attr_value, (list, set, frozenset)):
            for i in sorted([str(i).encode() for i in attr_value]):
                hashobj.update(i)
                if debug:
                    print(hashobj.hexdigest(), attr_name, i)
        else:
            hashobj.update(str(attr_value).encode())
            if debug:
                print(hashobj.hexdigest(), attr_name, str(attr_value).encode())

    for k, v in sorted(txn.meta.items()):
        if k in meta_subset:
            hashobj.update(str(v).encode())
            if debug:
                print(hashobj.hexdigest(), k, str(v).encode())
        elif k in ('filename', 'lineno', 'sha1v2') and len(meta_subset) == 0:
            pass
        elif len(meta_subset) == 0:
            hashobj.update(str(v).encode())
            if debug:
                print(hashobj.hexdigest(), k, str(v).encode())

    return hashobj.hexdigest()


def dedect_duplicates(new_entries_by_file, existing_entries):
    existing_entries_by_hash = {}
    meta_subset = ['iban', 'bic']
    if existing_entries is not None:
        for entry in existing_entries:
            existing_entries_by_hash[hash_entry(entry, meta_subset)] = entry
    r = []

    for filename, new_entries in new_entries_by_file:
        xs = []
        for new_entry in new_entries:
            old_entry = existing_entries_by_hash.get(
                hash_entry(new_entry, meta_subset))

            if old_entry is not None:
                new_meta = {
                    **new_entry.meta,
                    **old_entry.meta,
                }

                xs.append(
                    old_entry._replace(meta={
                        k: v
                        for k, v in new_meta.items() if k != 'sha1v2'
                    }))
            else:
                xs.append(new_entry)

        r.append((filename, xs))
    return r


def ingest(importers_list, detect_duplicates_func=None, hooks=None):
    """Driver function that calls all the ingestion tools.

    Put a call to this function at the end of your importer configuration to
    make your import script; this should be its main function, like this:

      from beancount.ingest.scripts_utils import ingest
      my_importers = [ ... ]
      ingest(my_importers)

    This more explicit way of invoking the ingestion is now the preferred way to
    invoke the various tools, and replaces calling the bean-identify,
    bean-extract, bean-file tools with a --config argument. When you call the
    import script itself (as as program) it will parse the arguments, expecting
    a subcommand ('identify', 'extract' or 'file') and corresponding
    subcommand-specific arguments.

    Here you can override some importer values, such as installing a custom
    duplicate finding hook, and eventually more. Note that this newer invocation
    method is optional and if it is not present, a call to ingest() is generated
    implicitly, and it functions as it used to. Future configurable
    customization of the ingestion process will be implemented by inserting new
    arguments to this function, this is the motivation behind doing this.

    Note that invocation by the three bean-* ingestion tools is still supported,
    and calling ingest() explicitly from your import configuration file will not
    break these tools either, if you invoke them on it; the values you provide
    to this function will be used by those tools.

    Args:
      importers_list: A list of importer instances. This is used as a
        chain-of-responsibility, called on each file.
      detect_duplicates_func: (DEPRECATED) An optional function which accepts a
        list of lists of imported entries and a list of entries already existing
        in the user's ledger. See function find_duplicate_entries(), which is
        the default implementation for this. Use 'filter_funcs' instead.
      hooks: An optional list of hook functions to apply to the list of extract
        (filename, entries) pairs, in order. This replaces
        'detect_duplicates_func'.
    """
    if detect_duplicates_func is not None:
        warnings.warn("Argument 'detect_duplicates_func' is deprecated.")
        # Fold it in hooks.
        if hooks is None:
            hooks = []
        hooks.insert(0, detect_duplicates_func)
        del detect_duplicates_func

    # The script is called directly. This is the main program of the import
    # script itself. This is the new invocation method.
    parser = scripts_utils.version.ArgumentParser(
        description=scripts_utils.DESCRIPTION)

    # Use required on subparsers.
    # FIXME: Remove this when we require version 3.7 or above.
    kwargs = {}
    if sys.version_info >= (3, 7):
        kwargs['required'] = True
    subparsers = parser.add_subparsers(dest='command', **kwargs)

    parser.add_argument(
        '--downloads',
        '-d',
        metavar='DIR-OR-FILE',
        action='append',
        default=[],
        help='Filenames or directories to search for files to import')

    for cmdname, module in [
        ('identify', scripts_utils.identify),
        ('extract', scripts_utils.extract),
        ('file', scripts_utils.file),
    ]:
        parser_cmd = subparsers.add_parser(cmdname, help=module.DESCRIPTION)
        parser_cmd.set_defaults(command=module.run)
        module.add_arguments(parser_cmd)

    args = parser.parse_args()

    if not args.downloads:
        args.downloads.append(os.getcwd())

    # Implement required ourselves.
    # FIXME: Remove this when we require version 3.7 or above.
    if not (sys.version_info >= (3, 7)):
        if not hasattr(args, 'command'):
            parser.error("Subcommand is required.")

    abs_downloads = list(map(path.abspath, args.downloads))
    if isinstance(args.command, str):
        dict([
            ('identify', scripts_utils.identify),
            ('extract', scripts_utils.extract),
            ('file', scripts_utils.file),
        ])[args.command].run(args,
                             parser,
                             importers_list,
                             abs_downloads,
                             hooks=hooks)
    else:
        args.command(args, parser, importers_list, abs_downloads, hooks=hooks)
    return 0
