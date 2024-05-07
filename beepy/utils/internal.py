import asyncio
import os
import random
import sys
from importlib import import_module
from typing import TYPE_CHECKING

import dotenv
import micropip

from beepy.utils.js_py import IN_BROWSER, js, to_js

if TYPE_CHECKING:
    from collections.abc import Callable

_beepy_root_package = '__beepy_root__'
_py_tag_attribute = '__PYTHON_TAG__'

dotenv.load_dotenv(f'{_beepy_root_package}/.env' if IN_BROWSER else '.env')

# TODO: make it with dataclass?
# TODO: consider using .toml/.yaml usage instead of .env + window.beepy.config
__config__ = {
    'debug': os.environ.get('DEBUG') == '1',
    'development': os.environ.get('DEVELOPMENT') == '1',
    'style_head': True,
    'api_url': '/',
    'default_datetime_format': '%Y-%m-%dT%H:%M:%S.%f%Z',
    'inputs_auto_id': True,
    'html_replace_whitespaces': True,
    'random_seed': int(os.environ.get('RANDOM_SEED', 0)),
    'server_side': '',
    'requirements': [],
}


def merge_configs():
    __config__.update(js.beepy.config.to_py())
    js.beepy.config = to_js(__config__)


if IN_BROWSER:  # TODO: check support for non-browser runs
    merge_configs()


async def reload_requirements():
    get_requirements: list | Callable = __config__['requirements']
    if not callable(get_requirements):  # static requirements, must be already loaded
        return

    await asyncio.gather(*[micropip.install(requirement) for requirement in get_requirements()])


def lazy_import(module_path):
    if not (
        (module := sys.modules.get(module_path))
        and (spec := getattr(module, '__spec__', None))
        and getattr(spec, '_initializing', False) is False
    ):
        module = import_module(module_path)

    return module


def import_string(dotted_path):
    module_path, class_name = dotted_path.rsplit('.', 1)
    return getattr(lazy_import(module_path), class_name)


def lazy_import_cls(cls):
    if isinstance(cls, str):
        return import_string(cls)
    return cls


def get_seed():
    if not __config__['random_seed']:
        __config__['random_seed'] = int.from_bytes(os.urandom(8), 'big')
    return __config__['random_seed']


def _init_js():
    from beepy import __version__

    js.console.log(f'%cBeePy version: {__version__}', 'color: lightgreen; font-size: 35px')
    merge_configs()
    rnd.seed(get_seed())


class _BeePyGlobals(dict):
    def __getitem__(self, key):
        result = super().__getitem__(key)
        for handler in __beepy_global_handlers__:
            result = handler(self, key, result)
        return result


def _default_global_handlers(locals_dict, key, result):
    if key.startswith('_p__'):
        return result(locals_dict)
    return result


__beepy_global_handlers__ = [_default_global_handlers]
rnd = random.Random()


__all__ = [
    '_py_tag_attribute',
    '__config__',
    'merge_configs',
    'lazy_import',
    'import_string',
    'lazy_import_cls',
    'reload_requirements',
    '__beepy_global_handlers__',
    'rnd',
]
