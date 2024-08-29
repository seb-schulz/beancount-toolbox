import argparse
import importlib
import os
import sys
import typing
from collections.abc import Callable
from beancount import loader
from beancount.parser import printer
from beancount.core import data
import pydantic


class PluginConfig(pydantic.BaseModel):
    module_name: str
    string_config: str = None

    @pydantic.computed_field
    @property
    def module_fn(
        self
    ) -> Callable[[typing.List[typing.NamedTuple], typing.Mapping],
                  typing.Tuple[typing.List[typing.NamedTuple], typing.List]]:
        if self.module_name is None:
            return []

        try:
            cb_fns = [getattr(sys.modules[__name__], self.module_name)]
        except AttributeError:
            module = importlib.import_module(self.module_name)
            if not hasattr(module, '__plugins__'):
                return []

            module = importlib.import_module(self.module_name)
            if not hasattr(module, '__plugins__'):
                return []

            cb_fns = [
                getattr(module, fn) if isinstance(fn, str) else fn
                for fn in module.__plugins__
            ]

        def wrapper(entires, options_map):
            for cb in cb_fns:
                if self.string_config is None:
                    new_entires, errors = cb(
                        entires,
                        options_map,
                    )
                else:
                    new_entires, errors = cb(
                        entires,
                        options_map,
                        self.string_config,
                    )
                return data.sorted(new_entires), errors
            return

        return wrapper


def exec_plugin(entries, options_map: typing.Mapping,
                config: PluginConfig | None):

    if config is None:
        return entries, []
    return config.module_fn(entries, options_map)


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
