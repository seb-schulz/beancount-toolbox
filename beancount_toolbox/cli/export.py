import argparse
import importlib
import os
import re
import sys
import pydantic.json
import yaml
import typing
from collections.abc import Callable
from beancount import loader
from beancount.parser import printer
from beancount.core import data, amount
from beancount.utils import misc_utils
from beancount.ops import compress
import pydantic


class BeancountPluginConfig(pydantic.BaseModel):
    module_name: str = pydantic.Field(
        description=
        'Plugin of beancount ecosystem (e.x. beancount.plugins.auto_accounts)',
        examples='beancount.plugins.auto_accounts',
    )
    string_config: str = None

    @pydantic.computed_field
    @property
    def plugin_fn(
        self
    ) -> Callable[[typing.List[typing.NamedTuple], typing.Mapping],
                  typing.Tuple[typing.List[typing.NamedTuple], typing.List]]:

        module = importlib.import_module(self.module_name)
        if not hasattr(module, '__plugins__'):
            return []

        cb_fns = [
            getattr(module, fn) if isinstance(fn, str) else fn
            for fn in module.__plugins__
        ]

        def wrapper(entires, options_map):
            errors = []
            for cb in cb_fns:
                if self.string_config is None:
                    new_entires, e = cb(
                        entires,
                        options_map,
                    )
                else:
                    new_entires, e = cb(
                        entires,
                        options_map,
                        self.string_config,
                    )
                new_entires = data.sorted(new_entires)
                errors.extend(e)
            return new_entires, errors

        return wrapper

    def apply(
        self, entries, options_map: typing.Mapping
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        return self.plugin_fn(entries, options_map)


class CallableConfig(pydantic.BaseModel):
    fun: Callable[[typing.List[typing.NamedTuple], typing.Mapping],
                  typing.Tuple[typing.List[typing.NamedTuple], typing.List]]

    def apply(
        self, entries, options_map: typing.Mapping
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        new_entires, errors = self.fun(entries, options_map)
        return data.sorted(new_entires), errors


class TransactionOnlyConfig(pydantic.BaseModel):
    plugins: typing.List[BeancountPluginConfig
                         | pydantic.json_schema.
                         SkipJsonSchema[CallableConfig]] = []
    keep_directives: bool = False

    def apply(
        self, entries, options_map: typing.Mapping
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        entry_map = misc_utils.groupby(
            lambda x: isinstance(x, data.Transaction), entries)
        new_entries, new_errors = entry_map[True], []

        for p in self.plugins:
            ne, err = p.apply(new_entries, options_map)
            new_entries = data.sorted(ne)
            new_errors.extend(err)

        if self.keep_directives:
            new_entries.extend(entry_map[False])
        return data.sorted(new_entries), new_errors


def _pop_default(s):
    s.pop('default')


class RenameAccount(pydantic.BaseModel):
    old: str
    new: str

    def _apply(
            self, entries
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        old, new = self.old, self.new
        new_entries = []
        for entry in entries:
            if isinstance(entry, data.Transaction):
                new_postings = []
                for posting in entry.postings:
                    g = re.search(
                        old.strip(),
                        posting.account,
                    )
                    if g:
                        new_postings.append(
                            posting._replace(account=new.format(
                                **g.groupdict())))
                    else:
                        new_postings.append(posting)
                new_entries.append(entry._replace(postings=new_postings))
            else:
                new_entries.append(entry)
        return new_entries, []


class RenameCommodity(pydantic.BaseModel):
    old: str
    new: str

    def _apply(
            self, entries
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        old, new = self.old, self.new

        def search_and_replace_amount(
                units: data.Amount | None) -> data.Amount:
            if units is None:
                return
            g = re.search(old.strip(), units.currency)
            if g:
                return data.Amount(
                    number=units.number,
                    currency=new.format(**g.groupdict()),
                )
            return units

        def search_and_replace_cost(
            cost: typing.Union[data.Cost, data.CostSpec]
        ) -> typing.Union[data.Cost, data.CostSpec]:
            if cost is None:
                return
            g = re.search(old.strip(), cost.currency)
            if g:
                return cost._replace(currency=new.format(**g.groupdict()))
            return cost

        new_entries = []
        for entry in entries:
            if isinstance(entry, data.Transaction):
                new_postings = []
                for posting in entry.postings:
                    posting: data.Posting = posting
                    new_postings.append(
                        posting._replace(
                            units=search_and_replace_amount(posting.units),
                            cost=search_and_replace_cost(posting.cost),
                            price=search_and_replace_amount(posting.price),
                        ))
                new_entries.append(entry._replace(postings=new_postings))
            else:
                new_entries.append(entry)
        return new_entries, []


class Action(pydantic.BaseModel):
    keep_only_transactions: bool = pydantic.Field(
        None,
        description='Drop every directive except transactions',
        json_schema_extra=_pop_default)
    tidy_transactions: bool = pydantic.Field(
        None,
        description='Reduce postings of transaction to minimal set',
        json_schema_extra=_pop_default)
    rename_account: RenameAccount = pydantic.Field(
        None, description='Rename accounts', json_schema_extra=_pop_default)

    rename_commodity: RenameCommodity = pydantic.Field(
        None, description='Rename commodities', json_schema_extra=_pop_default)

    model_config = pydantic.ConfigDict(
        json_schema_extra={
            'oneOf': [
                dict(required=['keep_only_transactions']),
                dict(required=['rename_account']),
                dict(required=['rename_commodity']),
            ]
        })

    def _apply_keep_only_transactions(
            self, entries
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        if self.keep_only_transactions is None:
            return entries, []
        if not self.keep_only_transactions:
            return entries, []
        return [x for x in entries if isinstance(x, data.Transaction)], []

    def _apply_tidy_transactions(
            self, entries
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        new_entries = []
        for entry in entries:
            if isinstance(entry, data.Transaction):
                new_entry = compress.merge([entry], entry)

                new_entries.append(
                    new_entry._replace(postings=[
                        p for p in new_entry.postings
                        if p.units.number != amount.ZERO
                    ]))
            else:
                new_entries.append(entry)
        return new_entries, []

    def apply(
        self, entries, _options_map: typing.Mapping
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        if self.keep_only_transactions is not None:
            return self._apply_keep_only_transactions(entries)
        elif self.tidy_transactions:
            return self._apply_tidy_transactions(entries)
        elif self.rename_account is not None:
            return self.rename_account._apply(entries)
        elif self.rename_commodity is not None:
            return self.rename_commodity._apply(entries)


class RootConfig(pydantic.BaseModel):
    plugins: typing.List[Action | BeancountPluginConfig] = []

    def apply(
        self, entries, options_map: typing.Mapping
    ) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
        new_entries, new_errors = entries, []

        for p in self.plugins:
            ne, err = p.apply(new_entries, options_map)
            new_entries = data.sorted(ne)
            new_errors.extend(err)
        return new_entries, new_errors


@misc_utils.deprecated("export cli is going to be removed in version 2.0.0")
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--output',
        '-o',
        type=argparse.FileType('w'),
        default='-',
        help='Exported beanfile (prints output to stdout when undefined)',
    )
    parser.add_argument('config', help='Path to an export definition')
    parser.add_argument('beanfile', type=str, help='Path to a source file')
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print("no such config file", file=sys.stderr)
        sys.exit(1)
        return

    with open(args.config, 'r') as stream:
        try:
            config = RootConfig(**yaml.safe_load(stream))
        except TypeError:
            print("config file is invalid", file=sys.stderr)
            sys.exit(2)

    entries, errors, options_map = loader.load_file(args.beanfile)
    if len(errors) > 0:
        printer.print_errors(errors, file=sys.stderr)
        sys.exit(1)
        return

    entries, errors = config.apply(entries, options_map)
    if len(errors) > 0:
        printer.print_errors(errors, file=sys.stderr)
        sys.exit(1)
        return

    printer.print_entries(entries, file=args.output)


if __name__ == '__main__':
    main()
