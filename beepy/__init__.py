from pyodide.ffi import IN_BROWSER

if not IN_BROWSER:
    import sys
    from beepy.utils import js

    sys.modules['js'] = js
    del sys, js

import beepy.children  # must be loaded before .framework due to circular import
import beepy.utils.import_hooks  # allows to use `import` for local files
from beepy.tags import Head, Body
from beepy.style import Style
from beepy.attrs import attr, state, html_attr
from beepy.utils import __CONFIG__
from beepy.utils.dev import _debugger
from beepy.listeners import on
from beepy.types import safe_html, safe_html_content
from beepy.context import *
from beepy.context import __all__ as __context_all__
from beepy.components import *
from beepy.components import __all__ as __components_all__
from beepy.framework import *
from beepy.framework import __version__, __all__ as __framework_all__

__all__ = [
    'Head',
    'Body',
    'Style',
    '__CONFIG__',
    '_debugger',
    'attr',
    'state',
    'html_attr',
    'on',
    'safe_html',
    'safe_html_content',
    *__context_all__,
    *__framework_all__,
]
