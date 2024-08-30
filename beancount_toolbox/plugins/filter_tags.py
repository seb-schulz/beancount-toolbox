__plugins__ = ['filter_tags']
import typing
from beancount.ops import basicops
from beancount.core import getters, data


def filter_tags(entries, _options_map: typing.Mapping, config=None):
    if config is None:
        return entries, []

    new_entries = list(entries)
    for tag in config.split(' '):
        new_entries = list(basicops.filter_tag(tag, entries))

    return data.sorted(new_entries), []
