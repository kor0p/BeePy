from pyodide.ffi import IN_BROWSER

if not IN_BROWSER:
    import sys

    from beepy.utils import js

    sys.modules['js'] = js
    del sys, js

import beepy.children  # must be loaded before .framework due to circular import
import beepy.utils.import_hooks  # allows to use `import` for local files  # noqa: F401
from beepy.attrs import attr, attr_prop, html_attr, state, state_move_on, state_static
from beepy.components import Directive
from beepy.context import SpecialChild
from beepy.framework import Tag, __version__, empty_tag, mount
from beepy.listeners import on
from beepy.style import Style, import_css
from beepy.tags import Body, Head
from beepy.types import Children, safe_html, safe_html_content
from beepy.utils import __config__

__all__ = [
    'Head',
    'Body',
    'Style',
    'import_css',
    '__config__',
    'attr',
    'attr_prop',
    'state',
    'state_static',
    'state_move_on',
    'html_attr',
    'on',
    'safe_html',
    'safe_html_content',
    'Directive',
    'SpecialChild',
    'Tag',
    'Children',
    'empty_tag',
    'mount',
    '__version__',
]
