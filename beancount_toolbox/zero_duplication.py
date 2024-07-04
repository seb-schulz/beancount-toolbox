__plugins__ = ['zero_duplication']


def zero_duplication(entries, options_map):
    errors = []

    for entry in entries:
        if 'zero_duplication' in entry.meta:
            entry.postings.clear()

    return entries, errors
