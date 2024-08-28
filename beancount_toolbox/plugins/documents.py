__plugins__ = ['documents']

import os
import typing
from os import path

from beancount.core import data, flags


def _basepath_from_config(options_map: typing.Mapping = {}, config=None):
    if config is None:
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

    errors = []
    new_documents = []

    for entry in entries:
        for key in ['invoice', 'document']:
            if key not in entry.meta:
                continue

            file = entry.meta[key]
            if not path.isabs(file):
                file = path.join(basepath, file)

            for post in entry.postings:
                new_documents.append(
                    data.Document(
                        dict(**entry.meta),
                        entry.date,
                        post.account,
                        file,
                        entry.tags.copy(),
                        entry.links.copy(),
                    ))

    entries.extend(new_documents)
    return data.sorted(entries), errors
