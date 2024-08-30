__plugins__ = ['filter_tags']
import typing
from beancount.ops import basicops
from beancount.core import getters, data


def filter_tags(entries, options_map: typing.Mapping, config=None):
    if config is None:
        return entries, []

    open_close_dict = getters.get_account_open_close(entries)

    new_entries = list(entries)
    for tag in config.split(' '):
        new_entries = list(basicops.filter_tag(tag, entries))

    existing_open_close_set = set([
        (type(e), e.account)
        for xs in getters.get_account_open_close(new_entries).values()
        for e in xs if e is not None
    ])

    for accounts_ in getters.get_accounts(new_entries):
        new_entries.extend([
            x for x in open_close_dict.get(accounts_, [])
            if x is not None and (type(x),
                                  x.account) not in existing_open_close_set
        ])
    return data.sorted(new_entries), []
