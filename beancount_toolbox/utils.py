from os import path
import os
import typing


def basepath_from_config(default,
                         options_map: typing.Mapping = {},
                         config: str = None) -> os.PathLike:
    docpath = default if config is None else config

    if path.isabs(docpath):
        return docpath

    main_file = options_map.get('filename', '<empty>')
    if path.isfile(main_file):
        return path.join(path.dirname(main_file), docpath)

    return path.join(os.getcwd(), docpath)
