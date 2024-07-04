__plugins__ = ['tag_component']

from beancount.core import data


def tag_component(entries, options_map, components):
    errors = []
    components = components.split(' ')

    new_entries = []
    for entry in entries:
        for c in components:
            if data.has_entry_account_component(entry, c):
                entry = entry._replace(tags=set([c.lower()]) | entry.tags)
        new_entries.append(entry)
    return new_entries, errors
