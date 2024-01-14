import asyncio
import os
import sys
from importlib import import_module
from typing import TYPE_CHECKING

import dotenv
import micropip

from beepy.utils.js_py import IN_BROWSER, js, to_js

if TYPE_CHECKING:
    from collections.abc import Callable

BEEPY_ROOT_PACKAGE = '__beepy_root__'
_PY_TAG_ATTRIBUTE = '__PYTHON_TAG__'

dotenv.load_dotenv(f'{BEEPY_ROOT_PACKAGE}/.env' if IN_BROWSER else '.env')

# TODO: make it with dataclass
__CONFIG__ = {
    'debug': 'DEBUG' in os.environ,
    'development': 'DEVELOPMENT' in os.environ,
    'style_head': True,
    'api_url': '/',
    'default_datetime_format': '%Y-%m-%dT%H:%M:%S.%f%Z',
    'inputs_auto_id': True,
    'html_replace_whitespaces': True,
    'requirements': [],
}


def merge_configs():
    __CONFIG__.update(js.beepy.config.to_py())
    js.beepy.config = to_js(__CONFIG__)


if IN_BROWSER:  # TODO: check support for non-browser runs
    merge_configs()


async def reload_requirements():
    get_requirements: list | Callable = __CONFIG__['requirements']
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


def _init_js():
    from beepy import __version__

    js.console.log(f'%cBeePy version: {__version__}', 'color: lightgreen; font-size: 35px')
    merge_configs()


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


__all__ = [
    '_PY_TAG_ATTRIBUTE',
    '__CONFIG__',
    'merge_configs',
    'lazy_import',
    'import_string',
    'lazy_import_cls',
    'reload_requirements',
    '__beepy_global_handlers__',
]
