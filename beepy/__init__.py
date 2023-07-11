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
    from beepy.utils import js

    sys.modules['js'] = js
    del sys

import beepy.children  # must be loaded before .framework due to circular import
import beepy.utils.import_hooks  # allows to use `import` for local files
from beepy.tags import Head, Body
from beepy.style import Style
from beepy.context import *
from beepy.context import __all__ as __context_all__
from beepy.framework import *
from beepy.framework import __version__, __all__ as __framework_all__

__all__ = [
    'Head',
    'Body',
    'Style',
    *__context_all__,
    *__framework_all__,
]
