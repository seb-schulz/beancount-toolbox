from os import path
import os
import unittest
from beancount_toolbox import utils


def fixture_path() -> str:
    return path.join(
        path.dirname(__file__),
        'fixtures',
        'documents',
    )


class TestBasePathFromConfig(unittest.TestCase):

    def test_none_values(self):
        got = utils.basepath_from_config('documents')
        self.assertEqual(
            got,
            path.join(os.getcwd(), 'documents'),
        )

    def test_with_option_map_filename(self):
        got = utils.basepath_from_config(
            'documents', {'filename': path.join(fixture_path(), 'empty.bean')})
        self.assertEqual(got, path.join(fixture_path(), 'documents'))

    def test_relative_config_path(self):
        self.assertEqual(
            utils.basepath_from_config('documents', {}, 'foobar'),
            path.join(os.getcwd(), 'foobar'),
        )
        self.assertEqual(
            utils.basepath_from_config(
                'documents',
                {
                    'filename': path.join(fixture_path(), 'empty.bean'),
                },
                'foobar',
            ),
            path.join(fixture_path(), 'foobar'),
        )

    def test_abs_config_path(self):
        self.assertEqual(
            utils.basepath_from_config('documents', {}, fixture_path()),
            fixture_path(),
        )
        self.assertEqual(
            utils.basepath_from_config(
                'documents',
                {
                    'filename': path.join(fixture_path(), 'empty.bean'),
                },
                fixture_path(),
            ),
            fixture_path(),
        )
