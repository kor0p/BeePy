import os
import sys

from importlib.abc import MetaPathFinder
from importlib.util import spec_from_file_location

from beepy.utils.js_py import js, IN_BROWSER
from beepy.utils.internal import BEEPY_ROOT_PACKAGE, __CONFIG__
from beepy.utils.dev import _debugger


requirements = __CONFIG__['requirements']
MODULES_NOT_EXISTING_ON_SERVER = [
    BEEPY_ROOT_PACKAGE,
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
    def find_spec(self, fullname, path, target=None):
        if path and any(p.startswith('/lib') for p in path):
            return

        if os.path.exists(f'/lib/python3.11/site-packages/{fullname}'):
            return

        if fullname in MODULES_NOT_EXISTING_ON_SERVER:
            return

        is_beepy_module = fullname.startswith('beepy.')
        current_path = js.beepy.files._lastLoadedFile
        if is_beepy_module:
            js.beepy.files._lastLoadedFile = __CONFIG__['path']

        err = None
        try:
            js.beepy._loadLocalModule(fullname)
        except Exception as e:
            err = e

        if err or is_beepy_module:
            js.beepy.files._lastLoadedFile = current_path

        if err:
            _debugger(err)
            MODULES_NOT_EXISTING_ON_SERVER.append(fullname)
            return

        return spec_from_file_location(fullname)


if IN_BROWSER:
    sys.meta_path.insert(0, ServerFinder())
    sys.path.append(BEEPY_ROOT_PACKAGE)
