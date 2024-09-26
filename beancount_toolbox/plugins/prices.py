__plugins__ = ['prices']

import csv
import datetime
import os
import typing
from os import path

from dateutil import rrule
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


def _amount_with_comma(val, c, conv=lambda x: x):
    val = conv(data.D(val.replace('.', '').replace(',', '.')))
    return amount.from_string(f'{val} {c}')


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
            if x[5] == '%':
                op_c = operating_currency[0]
                def conv(x): return x / 100
            else:
                op_c = x[5]
                def conv(x): return x
            try:
                a = _amount_with_comma(x[4], op_c, conv=conv)
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
                        'open': str(_amount_with_comma(x[1], op_c, conv=conv)),
                        'high': str(_amount_with_comma(x[2], op_c, conv=conv)),
                        'low': str(_amount_with_comma(x[3], op_c, conv=conv)),
                        'volume': x[6].replace('.', ''),
                    }), _parse_dt(x[0]), currency, a)

            if a.currency not in operating_currency:
                yield p, PriceError(
                    data.new_metadata(file, lineno),
                    'invalid currency',
                    p,
                )

            yield p, None


def _date_range(start: abc.Directive,
                end: abc.Directive) -> typing.List[datetime.date]:
    return sorted({
        x.date()
        for x in rrule.rrule(
            rrule.WEEKLY,
            dtstart=start.date,
            until=end.date,
            byweekday=rrule.SU,
        )
    } | {
        x.date()
        for x in rrule.rrule(
            rrule.MONTHLY,
            dtstart=start.date,
            until=end.date,
            bymonthday=-1,
        )
    })


def _groupby_date(
    entries: typing.List[abc.Directive], seq: typing.List[datetime.date]
) -> typing.Dict[datetime.date, typing.List[abc.Directive]]:
    r = {d: [] for d in seq}
    for entry in data.sorted(entries):
        for k in seq:
            if entry.date <= k:
                r[k].append(entry)
                break

    return r


def _merge_prices(entries: typing.List[abc.Price]) -> abc.Price | None:
    if len(entries) > 0:
        return data.Price(
            data.new_metadata(
                entries[0].meta.get('filename', ''),
                entries[0].meta.get('lineno', 0), {
                    'open': entries[0].meta['open'],
                    'high': max([e.meta['high'] for e in entries]),
                    'low': min([e.meta['low'] for e in entries]),
                    'volume': sum([data.D(e.meta['volume']) for e in entries]),
                }),
            entries[-1].date,
            entries[0].currency,
            entries[-1].amount,
        )


def prices(
    entries: typing.List,
    options_map: typing.Mapping,
    config=None,
) -> typing.Tuple[typing.List[typing.NamedTuple], typing.List]:
    basedir = utils.basepath_from_config('prices', options_map, config)
    errors = []
    for currency, ce in getters.get_commodity_directives(entries).items():
        for file in _glob(currency, basdir=basedir):
            new_entries = []
            for p, e in _parse_csv_file(file, currency, options_map):
                if p is not None and p.date >= ce.date:
                    new_entries.append(p)
                if e is not None:
                    errors.append(e)

            if len(new_entries) > 0:
                new_entries = [
                    _merge_prices(grouped) for grouped in _groupby_date(
                        new_entries,
                        _date_range(ce, new_entries[-1]),
                    ).values()
                ]
                entries.extend([x for x in new_entries if x is not None])
    return entries, errors
