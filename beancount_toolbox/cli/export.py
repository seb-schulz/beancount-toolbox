import argparse
import importlib
import os
import sys
import typing
from collections.abc import Callable
from beancount import loader
from beancount.parser import printer
from beancount.core import data
from beancount.utils import misc_utils
import pydantic


class BeancountPluginConfig(pydantic.BaseModel):
    module_name: str
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
    plugins: typing.List[BeancountPluginConfig | CallableConfig] = []
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

    entries, errors, options_map = loader.load_file(args.source)
    if len(errors) > 0:
        printer.print_errors(errors, file=sys.stderr)
        os.exit(1)
        return

    print(args)


if __name__ == '__main__':
    main()