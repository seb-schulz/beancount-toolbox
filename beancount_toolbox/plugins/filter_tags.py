__plugins__ = ['filter_tags']
import typing
from beancount.ops import basicops
from beancount.core import data


def filter_tags(entries, _options_map: typing.Mapping, config=None):
    if config is None:
        return entries, []

    new_entries: data.Directives = list(entries)
    for tag in config.split(' '):
        new_entries = list(basicops.filter_tag(tag, new_entries))

    return data.sorted(new_entries), []
