__plugins__ = ['documents']

import os
import typing
from os import path
import dateutil

from beancount.core import data, getters


class DocumentError(typing.NamedTuple):
    source: dict[str, typing.Any]
    message: str
    entry: typing.NamedTuple


def _basepath_from_config(options_map: typing.Mapping = {}, config=None):
    if config is None or config == 'strict':
        main_file = options_map.get('filename', '<empty>')
        if path.isfile(main_file):
            return path.join(path.dirname(main_file), 'documents')
        else:
            return os.getcwd()
    else:
        # if path.exists(config) and not path.isabs(config):
        # TODO: Check case with relative path
        pass


def documents(entries, options_map: typing.Mapping, config=None):
    basepath = _basepath_from_config(options_map, config)
    existing_files = [
        path.join(root[len(basepath) + 1:], f)
        for root, _, files in os.walk(basepath) for f in files
    ]

    strict_opt = config is not None and config == 'strict'

    errors = []
    new_documents = []

    for entry in entries:
        for key in ['invoice', 'document']:
            if key not in entry.meta:
                continue

            file = entry.meta[key]
            try:
                date = dateutil.parser.isoparse(file.split('.', 1)[0]).date()
            except ValueError:
                date = entry.date

            if not path.isabs(file):
                match_list = [x for x in existing_files if x.endswith(file)]
                if len(match_list) > 0:
                    file = path.join(basepath, match_list[0])
                elif strict_opt:
                    errors.append(
                        DocumentError(
                            entry.meta,
                            f"missing file {file}",
                            entry,
                        ))
                    continue
                else:
                    file = path.join(basepath, file)

            for acc in getters.get_entry_accounts(entry):
                new_documents.append(
                    data.Document(
                        dict(**entry.meta),
                        date,
                        acc,
                        file,
                        entry.tags.copy(),
                        entry.links.copy(),
                    ))

    entries.extend(new_documents)
    return data.sorted(entries), errors
