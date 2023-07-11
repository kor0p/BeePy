import sys
import asyncio
from typing import Callable
from importlib import import_module

import micropip

from beepy.utils.js_py import js, IN_BROWSER, to_js


_PY_TAG_ATTRIBUTE = '__PYTHON_TAG__'
__CONFIG__ = {
    'debug': True,
    'style_head': True,
    'api_url': '/',
    'default_datetime_format': '%Y-%m-%dT%H:%M:%S.%f%Z',
    'inputs_auto_id': True,
    'html_replace_whitespaces': True,
    'requirements': [],
}


def merge_configs():
    __CONFIG__.update(js.beepy.__CONFIG__.to_py())
    js.beepy.__CONFIG__ = to_js(__CONFIG__)


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
        and (spec := getattr(module, "__spec__", None))
        and getattr(spec, "_initializing", False) is False
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
