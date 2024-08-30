import argparse
import calendar
import dataclasses
import datetime
import os
import pathlib
import subprocess
import sys
import typing
import uuid
from importlib.resources import files

import dateutil
import dateutil.relativedelta
import pydantic
import yaml
from beancount import loader
from beancount.core import (convert, data, flags, getters, inventory,
                            realization)
from beancount.parser import printer
from beancount.utils import misc_utils
from pydantic.dataclasses import dataclass


def xdg_config_home() -> pathlib.Path:
    """Return a Path corresponding to XDG_CONFIG_HOME."""
    return os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")


DEFAULT_CONFIG_PATHS = [
    '.bean-rofi.yaml',
    xdg_config_home() / 'bean-rofi' / 'bean-rofi.yaml',
]


@dataclass
class BeanfileConfig:
    main: pathlib.Path
    add_to: pathlib.Path


@dataclass
class Config:
    default: pathlib.Path
    beanfiles: typing.List[BeanfileConfig] = dataclasses.field(
        default_factory=lambda: [])

    @pydantic.model_validator(mode='after')
    def validate_default_value(self):
        if self.default not in [x.main for x in self.beanfiles]:
            raise ValueError('incorrect default value {!r}'.format(
                str(self.default)))
        return self

    @property
    def current_beanfile(self) -> BeanfileConfig:
        for c in self.beanfiles:
            if c.main == self.default:
                return c


def read_config_file(file: pathlib.Path):

    for x in [file] + DEFAULT_CONFIG_PATHS:
        if x is None:
            continue
        try:
            with open(x) as fp:
                c = yaml.safe_load(fp)
            return Config(**c)
        except FileNotFoundError:
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

    @property
    def theme(self):
        return self[-1].theme

    @property
    def current_view(self):
        return self[-1]

    def __init__(self, config: BeanfileConfig):
        self._config = config
        self._load()

    def reload(self, config: BeanfileConfig = None):
        if config is not None:
            self._config = config
        self._load()

    def _load(self):
        self.entries, _errors, _options = loader.load_file(self._config.main)
        self.clear()
        self.append(ListAccountsView(self.entries))

    def message(self):
        return self[-1].message

    def push(self, view):
        self.append(view)

    def on_selected(self, stdout):
        self[-1].on_selected(self, stdout)


class BaseView:
    key_bindings = []
    message = None
    theme = 'default.rasi'

    def rofi_args(self) -> typing.List[str]:
        return []

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
        return ['-format', 'i', '-matching', 'fuzzy']

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

    @property
    def message(self):
        return f'Account: {self.selected_account}'

    def rofi_args(self) -> typing.List[str]:
        return ['-format', 'i', '-matching', 'prefix']

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
    message = 'Select bean file'

    def __init__(self, config):
        self.config: Config = config

    def rofi_args(self) -> typing.List[str]:
        return ['-matching', 'fuzzy', '-format', 'i']

    def rofi_input(self) -> typing.Iterable[str]:
        for c in self.config.beanfiles:
            yield str(c.main)

    def on_selected(self, viewstack: ViewStack, stdout):
        viewstack.reload(self.config.beanfiles[int(stdout)])


class AddEntryDatePickerView(BaseView):
    message = 'Add entry - pick date'
    theme = 'calendar.rasi'

    def __init__(self):
        now = datetime.datetime.now()
        cal = calendar.Calendar()

        self.calendar_input = {
            w: f'{w}\0nonselectable\x1ftrue'
            for w in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        }

        self.active_rows = set()
        idx = len(self.calendar_input)

        for i in reversed(range(0, 3)):
            cur = now + dateutil.relativedelta.relativedelta(months=-i)
            for y, m, d in cal.itermonthdays3(cur.year, cur.month):
                k = f'{y}-{m:02d}-{d:02d}'
                if k in self.calendar_input:
                    continue

                v = f'{d:02d}\0meta\x1f{y}-{m:02d}-{d:02d}'
                self.calendar_input[k] = v

                if d == 1:
                    self.active_rows.add(f'{idx}')
                if now.year == y and now.month == m and now.day == d:
                    self.active_rows.add(f'{idx}')

                idx += 1

    def rofi_args(self) -> typing.List[str]:
        return ['-p', 'date', '-format', 'i', '-a', ','.join(self.active_rows)]

    def rofi_input(self) -> typing.Iterable[str]:
        return list(self.calendar_input.values())

    def on_selected(self, viewstack: ViewStack, stdout):
        viewstack.push(
            AddEntryPayeeAndNarrationPickerView(
                list(self.calendar_input.keys())[int(stdout)]))


class AddEntryPayeeAndNarrationPickerView(BaseView):

    def __init__(self, date):
        self.date = date

    @property
    def message(self):
        return f'Add entry on {self.date} - enter payee and narration split by |'

    def rofi_args(self) -> typing.List[str]:
        return ['-p', 'payee|narration']

    def rofi_input(self) -> typing.Iterable[str]:
        return []

    def on_selected(self, viewstack: ViewStack, stdout):
        items = stdout.split('|', 1)
        if len(items) > 1:
            payee, narration = items
        else:
            payee, narration = None, items[0]

        viewstack.push(
            AddEntryAccountPickerView(
                viewstack.entries,
                date=self.date,
                payee=payee,
                narration=narration,
            ))


class AddEntryAccountPickerView(BaseView):
    key_bindings = ['Control+Return']

    def __init__(self, entries, *, date, payee, narration, postings=[]):
        self.entries = entries
        self.date = date
        self.payee, self.narration = payee, narration
        self.postings = postings

    @property
    def message(self):
        entry = data.Transaction(
            # {'uuid': str(uuid.uuid4())},
            {},
            self.date,
            flags.FLAG_OKAY,
            self.payee,
            self.narration,
            data.EMPTY_SET,
            data.EMPTY_SET,
            self.postings,
        )
        return '{0}\nAdd entry - pick account'.format(
            printer.format_entry(entry))

    def rofi_args(self) -> typing.List[str]:
        return [
            '-p', 'account', '-kb-accept-custom', 'Control+Shift+Alt+Return'
        ]

    def rofi_input(self) -> typing.Iterable[str]:
        return list(getters.get_accounts(self.entries))

    def on_key(self, viewstack: ViewStack, key_idx: int):
        if key_idx == 0:
            idx = -1
            inv = inventory.Inventory()
            for i, p in enumerate(self.postings):
                if p.units is None:
                    idx = i
                else:
                    inv.add_position(p)
            if idx >= 0:
                amount = -data.Amount.from_string(
                    inv.reduce(convert.get_cost).to_string(parens=False))
                self.postings[idx] = data.create_simple_posting(
                    None,
                    self.postings[idx].account,
                    amount.number,
                    amount.currency,
                )

            entry = data.Transaction(
                {'uuid': str(uuid.uuid4())},
                self.date,
                flags.FLAG_OKAY,
                self.payee,
                self.narration,
                data.EMPTY_SET,
                data.EMPTY_SET,
                self.postings,
            )

            with open(os.path.expanduser(viewstack._config.add_to), 'a') as fp:
                print(
                    '\n{}'.format(printer.format_entry(entry).strip()),
                    file=fp,
                )
            viewstack.reload()

    def on_selected(self, viewstack: ViewStack, stdout):

        viewstack.push(
            AddEntryNumberPickerView(
                self.entries,
                stdout,
                date=self.date,
                payee=self.payee,
                narration=self.narration,
                postings=self.postings,
            ))


class AddEntryNumberPickerView(BaseView):

    def __init__(self,
                 entries,
                 account,
                 *,
                 date,
                 payee,
                 narration,
                 postings=[]):
        self.entries = entries
        self.account = account
        self.date = date
        self.payee, self.narration = payee, narration
        self.postings = postings

    @property
    def message(self):
        entry = data.Transaction(
            {},
            self.date,
            flags.FLAG_OKAY,
            self.payee,
            self.narration,
            data.EMPTY_SET,
            data.EMPTY_SET,
            self.postings,
        )
        return '{0}\nAdd entry - enter numer for {1}'.format(
            printer.format_entry(entry), self.account)

    def rofi_args(self) -> typing.List[str]:
        return ['-p', f'{self.account}\t']

    def rofi_input(self) -> typing.Iterable[str]:
        return []

    def on_selected(self, viewstack: ViewStack, stdout):
        postings = list(self.postings)

        if len(stdout) == 0 or stdout == 'x':
            postings.append(
                data.create_simple_posting(None, self.account, None, None))
        else:
            amount = data.Amount.from_string(stdout)
            postings.append(
                data.create_simple_posting(
                    None,
                    self.account,
                    amount.number,
                    amount.currency,
                ))

        viewstack.push(
            AddEntryAccountPickerView(
                self.entries,
                date=self.date,
                payee=self.payee,
                narration=self.narration,
                postings=postings,
            ))


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

    view_stack = ViewStack(config.current_beanfile)

    while len(view_stack) > 0:
        try:
            args = [
                'rofi', '-dmenu', '-markup-rows', '-i', '-theme',
                files('beancount_toolbox.data').joinpath(view_stack.theme),
                '-kb-custom-1', 'Control+s', '-kb-custom-2', 'Control+a',
                '-kb-move-front', 'Control+Shift+a'
            ]
            default_msg = '<small><b>Switch file</b> (Ctrl+s), <b>Add entry</b> (Ctrl+a)</small>'
            msg = view_stack.message()
            if msg is not None:
                args.extend(['-mesg', f'{msg}\n{default_msg}'])
            else:
                args.extend(['-mesg', default_msg])
            args.extend(view_stack.current_view.rofi_args())

            for i, kb in enumerate(
                    view_stack.current_view.key_bindings,
                    start=3,
            ):
                args.extend([f'-kb-custom-{i}', kb])

            stdout = subprocess.run(
                args,
                input="\n".join(view_stack.current_view.rofi_input()),
                capture_output=True,
                check=True,
                text=True,
            ).stdout.strip()
            view_stack.on_selected(stdout)

        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                view_stack.pop()
            elif err.returncode == 10:
                view_stack.push(SelectBeanFile(config))
            elif err.returncode == 11:
                view_stack.push(AddEntryDatePickerView())
            elif 12 <= err.returncode < 12 + len(
                    view_stack.current_view.key_bindings):
                view_stack.current_view.on_key(view_stack, err.returncode - 12)
            else:
                raise err
    sys.exit()
