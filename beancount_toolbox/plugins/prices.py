__plugins__ = ['prices']

import csv
import datetime
import os
import typing
from os import path

import pydantic
from pydantic import functional_validators

from beancount_toolbox import utils
from beancount.core import getters, amount, data
from glob import glob
from fava.beans import abc

Amount = typing.Annotated[
    str, functional_validators.AfterValidator(amount.from_string)]


class PriceError(typing.NamedTuple):
    source: dict[str, typing.Any]
    message: str
    entry: typing.NamedTuple


def _glob(currency: str, *, basdir: os.PathLike):
    for file in glob(f'{currency}.csv', root_dir=basdir):
        yield path.join(basdir, file)
    for file in glob(f'{currency}/*.csv', root_dir=basdir):
        yield path.join(basdir, file)


def _parse_dt(dt):
    x = [int(i) for i in dt.split('.')]
    return datetime.date(year=x[2], month=x[1], day=x[0])


def _amount_with_comma(val, c):
    val = val.replace('.', '').replace(',', '.')
    return f'{val} {c}'


def _parse_csv_file(
    file, currency, options_map: typing.Mapping
) -> typing.Generator[typing.Tuple[abc.Price | None, PriceError | None], None,
                      None]:
    operating_currency = options_map.get('operating_currency', [])

    with open(file) as fp:
        sample = fp.read(1024)
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample)

        fp.seek(0)
        start = 1
        if sniffer.has_header(sample):
            next(fp)
            start += 1

        for lineno, x in enumerate(csv.reader(fp, dialect), start=start):
            try:
                a = amount.from_string(_amount_with_comma(x[4], x[5]))
            except ValueError as err:
                yield None, PriceError(
                    data.new_metadata(file, lineno),
                    str(err),
                    None,
                )
                continue

            p = data.Price(
                data.new_metadata(
                    file, lineno, {
                        'open': _amount_with_comma(x[1], x[5]),
                        'high': _amount_with_comma(x[2], x[5]),
                        'low': _amount_with_comma(x[3], x[5]),
                        'volume': x[6].replace('.', ''),
                    }), _parse_dt(x[0]), currency, a)
            if a.currency not in operating_currency:
                yield p, PriceError(
                    data.new_metadata(file, lineno),
                    'invalid currency',
                    p,
                )

            yield p, None


def prices(
    entries: typing.List,
    options_map: typing.Mapping,
    config=None,
) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
    basedir = utils.basepath_from_config('prices', options_map, config)
    errors = []
    for currency in getters.get_commodity_directives(entries).keys():
        for file in _glob(currency, basdir=basedir):
            for p, e in _parse_csv_file(file, currency, options_map):
                if p is not None:
                    entries.append(p)
                if e is not None:
                    errors.append(e)
    return entries, errors
