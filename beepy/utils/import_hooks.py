import sys

from importlib.abc import MetaPathFinder
from importlib.util import spec_from_file_location

from beepy.utils.js_py import js, IN_BROWSER
from beepy.utils.internal import __CONFIG__
from beepy.utils.dev import _debugger


BEEPY_ROOT_PACKAGE = '__beepy_root__'
requirements = __CONFIG__['requirements']
MODULES_NOT_EXISTING_ON_SERVER = [
    BEEPY_ROOT_PACKAGE,
    *(requirements() if callable(requirements) else requirements),
    '_hashlib',
    '_strptime',
    'unicodedata',
    'pprint',
]
# some modules must be ignored to prevent load it from local server, when importing modules like micropip or datetime


class ServerFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if path and any(p.startswith('/lib') for p in path):
            return

        if fullname in MODULES_NOT_EXISTING_ON_SERVER:
            return

        is_beepy_module = fullname.startswith('beepy.')
        current_path = js.beepy.__CURRENT_LOADING_FILE__
        if is_beepy_module:
            js.beepy.__CURRENT_LOADING_FILE__ = __CONFIG__['path']

        try:
            err = js.beepy._loadLocalModule(fullname, checkPathExists=True)
        except Exception as e:
            err = e

        if err or is_beepy_module:
            js.beepy.__CURRENT_LOADING_FILE__ = current_path

        if err:
            _debugger(err)
            MODULES_NOT_EXISTING_ON_SERVER.append(fullname)
            return

        return spec_from_file_location(fullname)


if IN_BROWSER:
    sys.meta_path.insert(0, ServerFinder())
    sys.path.append(BEEPY_ROOT_PACKAGE)
