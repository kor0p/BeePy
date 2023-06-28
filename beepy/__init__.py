# This file is actually not imported in Frontend (due to some restrictions)

try:
    from pyodide.ffi import IN_BROWSER
except ImportError:
    try:
        from pyodide import IN_BROWSER
    except ImportError:
        print('Did you forget to install optional requirements with `pip install -U beepy-web[dev]`?')
        exit(1)

if not IN_BROWSER:
    import sys
    from . import js

    sys.modules['js'] = js
    del sys

from beepy import local_storage, trackable, utils, types
from beepy import listeners, attrs, children
from beepy import context, framework, style, tags, actions, router, import_hooks
from beepy.tags import Head, Body
from beepy.style import Style
from beepy.context import *
from beepy.context import __all__ as __context_all__
from beepy.framework import *
from beepy.framework import __version__, __all__ as __framework_all__

__all__ = [
    'local_storage', 'trackable', 'utils', 'types',
    'listeners', 'attrs', 'children',
    'context', 'framework', 'style', 'tags', 'actions', 'router', 'import_hooks',
    'Head', 'Body', 'Style',
    *__context_all__,
    *__framework_all__,
]
