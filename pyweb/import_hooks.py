import sys

from importlib.abc import MetaPathFinder
from importlib.util import spec_from_file_location

import js
from pyweb.utils import IN_BROWSER, __CONFIG__, _debugger


PYWEB_ROOT_PACKAGE = '__pyweb_root__'
requirements = __CONFIG__['requirements']
MODULES_NOT_EXISTING_ON_SERVER = [
    PYWEB_ROOT_PACKAGE,
    *(requirements() if callable(requirements) else requirements),
    '_hashlib',
    '_strptime',
    'pprint',
]
# some modules must be ignored to prevent load it from local server, when importing modules like micropip or datetime
# TODO: move this hook higher to support importing `pyweb/__init__.py` natively


class ServerFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if path and any(p.startswith('/lib') for p in path):
            return

        if fullname in MODULES_NOT_EXISTING_ON_SERVER:
            return

        is_pyweb_module = fullname.startswith('pyweb.')
        current_path = js.pyweb.__CURRENT_LOADING_FILE__
        if is_pyweb_module:
            js.pyweb.__CURRENT_LOADING_FILE__ = __CONFIG__['path']

        try:
            err = js.pyweb._loadLocalModule(fullname, checkPathExists=True)
        except Exception as e:
            err = e

        if err or is_pyweb_module:
            js.pyweb.__CURRENT_LOADING_FILE__ = current_path

        if err:
            _debugger(err)
            MODULES_NOT_EXISTING_ON_SERVER.append(fullname)
            return

        return spec_from_file_location(fullname)


if IN_BROWSER:
    sys.meta_path.insert(0, ServerFinder())
    sys.path.append(PYWEB_ROOT_PACKAGE)
