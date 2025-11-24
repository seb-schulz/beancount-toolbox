import os
import typing
from os import path


def fixture_path(*target: str) -> str:
    return path.join(
        path.dirname(__file__),
        'fixtures',
        *target,
    )
