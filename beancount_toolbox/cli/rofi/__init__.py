import argparse
import os
import pathlib
import subprocess
import sys
import typing
import dataclasses

import dateutil.relativedelta
import pydantic
import yaml
from pydantic.dataclasses import dataclass
from beancount import loader
from beancount.core import getters, account_types, realization, convert, data, inventory
from beancount.utils import misc_utils
import dateutil
from importlib.resources import files


def xdg_config_home() -> pathlib.Path:
    """Return a Path corresponding to XDG_CONFIG_HOME."""
    return os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")


DEFAULT_CONFIG_PATHS = [
    '.bean-rofi.yaml',
    xdg_config_home() / 'bean-rofi' / 'bean-rofi.yaml',
]


@dataclass
class Config:
    default: pathlib.Path
    beanfiles: typing.List[pathlib.Path] = dataclasses.field(
        default_factory=lambda: [])

    @pydantic.model_validator(mode='after')
    def validate_default_value(self):
        if self.default not in self.beanfiles:
            raise ValueError('incorrect default value {!r}'.format(
                str(self.default)))
        return self


def read_config_file(file: pathlib.Path):

    for x in [file] + DEFAULT_CONFIG_PATHS:
        if x is None:
            continue
        try:
            with open(x) as fp:
                c = yaml.safe_load(fp)
            return Config(**c)
        except FileNotFoundError as err:
            pass
        except pydantic.ValidationError as err:
            print(
                '\n'.join(x['msg'] for x in err.errors(
                    include_context=False,
                    include_input=False,
                    include_url=False,
                )),
                file=sys.stderr,
            )
            sys.exit(2)


class ViewStack(list):

    def __init__(self, beanfile):
        self._load(beanfile)

    def reload(self, beanfile):
        self._load(beanfile)

    def _load(self, beanfile):
        entries, _errors, _options = loader.load_file(beanfile)
        self.clear()
        self.append(ListAccountsView(entries))

    def push(self, view):
        self.append(view)

    def on_selected(self, stdout):
        self[-1].on_selected(self, stdout)


class BaseView:

    def rofi_args(self) -> typing.List[str]:
        raise NotImplementedError('requires implementation of sub class')

    def rofi_input(self) -> typing.Iterable[str]:
        return []

    def on_selected(self, viewstack, stdout):
        print(stdout)


class ListAccountsView(BaseView):

    def __init__(self, entries):
        self.entries = entries
        root = realization.realize(entries)
        # root = realization.filter(
        #     root,
        #     lambda x: account_types.is_account_type(
        #         account_types.DEFAULT_ACCOUNT_TYPES.assets,
        #         x.account,
        #     ),
        # )
        self.input = list(realization.iter_children(root, leaf_only=True))

    def rofi_args(self) -> typing.List[str]:
        return ['-mesg', 'Hello\nworld', '-format', 'i', '-matching', 'fuzzy']

    def rofi_input(self) -> typing.Iterable[str]:
        for x in self.input:
            yield '{0:<80}{1:>20}'.format(
                x.account,
                x.balance.reduce(convert.get_cost).to_string(parens=False),
            )

    def on_selected(self, viewstack, stdout):
        selected_account = self.input[int(stdout)].account
        viewstack.push(
            JournalView(
                self.entries,
                selected_account,
                r'{:%Y-%m}',
            ))


class JournalView(BaseView):

    def __init__(self,
                 entries,
                 selected_account,
                 date_format=r'{:%F}',
                 date_begin=None,
                 date_end=None):
        self.entries = entries
        self.selected_account = selected_account
        self.date_format = date_format

        entry_iter = data.filter_txns(self.entries)
        if date_begin is not None and date_end is not None:
            entry_iter = data.iter_entry_dates(
                list(entry_iter),
                date_begin,
                date_end,
            )

        grouped_input = {
            date:
            inventory.Inventory([
                posting for entry in entries for posting in entry.postings
                if posting.account == self.selected_account
            ])
            for date, entries in
            misc_utils.groupby(lambda x: self.date_format.format(x.date), (
                entry for entry in entry_iter
                if self.selected_account in getters.get_entry_accounts(entry)
            )).items()
        }

        self.input = list(reversed(grouped_input.items()))

    def rofi_args(self) -> typing.List[str]:
        return [
            '-mesg', f'Account: {self.selected_account}', '-format', 'i',
            '-matching', 'prefix'
        ]

    def rofi_input(self) -> typing.Iterable[str]:
        for date, inv in self.input:
            yield '{0:<80}{1:>20}'.format(
                date,
                inv.reduce(convert.get_cost).to_string(parens=False),
            )

    def on_selected(self, viewstack, stdout):
        date = dateutil.parser.isoparse(self.input[int(stdout)][0])
        viewstack.push(
            JournalView(
                self.entries,
                self.selected_account,
                date_begin=date.date(),
                date_end=(
                    date +
                    dateutil.relativedelta.relativedelta(months=1)).date(),
            ))


class SelectBeanFile(BaseView):

    def __init__(self, beanfiles):
        self.beanfiles = beanfiles

    def rofi_args(self) -> typing.List[str]:
        return ['-mesg', 'Select bean file', '-matching', 'fuzzy']

    def rofi_input(self) -> typing.Iterable[str]:
        for path in self.beanfiles:
            yield str(path)

    def on_selected(self, viewstack: ViewStack, stdout):
        viewstack.reload(stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        '-c',
        help='Configuration file',
        type=pathlib.Path,
    )
    args = parser.parse_args(sys.argv[1:])
    config = read_config_file(args.config)
    if config is None:
        print(
            'provide config file with -c or create file under {}'.format(
                ' or '.join(str(x) for x in DEFAULT_CONFIG_PATHS)),
            file=sys.stderr,
        )
        sys.exit(1)

    view_stack = ViewStack(config.default)

    while len(view_stack) > 0:
        try:
            stdout = subprocess.run(
                [
                    'rofi', '-dmenu', '-markup-rows', '-i', '-theme',
                    files('beancount_toolbox.data').joinpath('default.rasi'),
                    '-kb-custom-1', 'Control+s'
                ] + view_stack[-1].rofi_args(),
                input="\n".join(view_stack[-1].rofi_input()),
                capture_output=True,
                check=True,
                text=True,
            ).stdout.strip()
            view_stack.on_selected(stdout)

        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                view_stack.pop()
            elif err.returncode == 10:
                view_stack.push(SelectBeanFile(config.beanfiles))
            else:
                raise err
    sys.exit()
