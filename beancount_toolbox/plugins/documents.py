__plugins__ = ['documents']

from beancount.core import data, flags
from os import path
import os


def documents(entries, options_map, config=None):
    if config is None:
        main_file = options_map.get('filename')
        if path.isfile(main_file):
            config = path.join(path.dirname(main_file), 'documents')
        else:
            config = os.getcwd()
    else:
        # if path.exists(config) and not path.isabs(config):
        # TODO: Check case with relative path
        pass

    errors = []
    new_documents = []

    for entry in entries:
        if 'invoice' in entry.meta:
            file = entry.meta['invoice']
            if not path.isabs(file):
                file = path.join(config, file)

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
