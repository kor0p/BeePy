import sys
from importlib.abc import MetaPathFinder
from importlib.util import spec_from_file_location
from pathlib import Path

from pyodide.ffi import JsException

from beepy.utils.dev import _debugger
from beepy.utils.internal import __config__, _beepy_root_package
from beepy.utils.js_py import IN_BROWSER, js

requirements = __config__['requirements']
_modules_not_existing_on_server = [
    _beepy_root_package,
    *(requirements() if callable(requirements) else requirements),
    '_hashlib',  # TODO: FIX THIS...
    '_strptime',
    'unicodedata',
    'pprint',
    'numpy',
    'matplotlib',
    'numbers',
    'pickle5',
    'pickle',
    '_compat_pickle',
    '_pickle',
    'org',
    'ctypes',
    '_ctypes',
    'backports_abc',
    'secrets',
    'hmac',
    'gzip',
    'shlex',
    'defusedxml',
    'cffi',
    'uuid',
    '_uuid',
    'cycler',
    'six',
    'six.moves',
    'six.moves.winreg',
    'decimal',
    '_decimal',
    'http',
    'ssl',
]
# some modules must be ignored to prevent load it from local server, when importing modules like micropip or datetime


class ServerFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):  # noqa: ARG002 - override of MetaPathFinder
        if path and any(p.startswith('/lib') for p in path):
            return

        if Path(f'/lib/python3.11/site-packages/{fullname}').exists() or fullname in _modules_not_existing_on_server:
            return

        current_path = js.beepy.files._lastLoadedFile

        try:
            js.beepy.loadModule(fullname)
        except JsException as err:
            js.beepy.files._lastLoadedFile = current_path
            _debugger(err)
            _modules_not_existing_on_server.append(fullname)
            return

        return spec_from_file_location(fullname)


if IN_BROWSER:
    sys.meta_path.insert(0, ServerFinder())
    sys.path.append(_beepy_root_package)
