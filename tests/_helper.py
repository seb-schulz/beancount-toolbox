import os
from os import path
import typing


def fixture_path(*target: typing.List[str]) -> os.PathLike:
    return path.join(
        path.dirname(__file__),
        'fixtures',
        *target,
    )
