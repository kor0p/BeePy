"""
This file is partly mock of JS API, created to make possible run and debug BeePy apps using console
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from threading import Thread
from typing import TYPE_CHECKING, Self

try:
    from pyodide.ffi import IN_BROWSER, create_once_callable, create_proxy
except ImportError:
    from pyodide import IN_BROWSER, create_once_callable, create_proxy


class HTMLElement:
    __PYTHON_TAG__: Tag

    def __init__(self, tag_name, *, _parent=None):
        self.attributes = {}
        self.data = []
        self.listeners = defaultdict(list)
        self.tagName = tag_name
        self.shadowRoot = None
        self.clientWidth = self.clientHeight = self.scrollWidth = self.scrollHeight = 1
        self.parentElement = _parent

    def getAttribute(self, name):
        return self.attributes.get(name)

    def setAttribute(self, name, value):
        self.attributes[name] = value

    def removeAttribute(self, name):
        self.attributes.pop(name, None)

    def append(self, string: str):
        self.data.append(string)
        print(self)

    def appendChild(self, el: HTMLElement):
        self.data.append(el)
        print(self)

    def insertChild(self, el: HTMLElement | str, index: int = None):
        if not isinstance(el, str):
            el.parentElement = self

        if index is None:
            self.data.append(el)
        else:
            self.data.insert(index, el)
        print(self)

    def removeChild(self, child: HTMLElement):
        self.data.remove(child)

    def safeRemoveChild(self, child: HTMLElement):
        if child in self.data:
            self.data.remove(child)

    def addEventListener(self, name, js_proxy):
        self.listeners[name].append(js_proxy)

    def attachShadow(self, **kwargs):
        self.shadowRoot = HTMLElement('-')
        return self.shadowRoot

    @property
    def innerHTML(self):
        return repr(self)

    @innerHTML.setter
    def innerHTML(self, value):
        self.data = [value]
        print(self)

    def __repr__(self):
        attrs = ' '
        for key, value in self.attributes.items():
            attrs += f'{key}="{value}" '
        attrs = attrs.strip(' ')
        if attrs:
            attrs = ' ' + attrs
        if not self.data:
            return f'<{self.tagName}{attrs}/>'
        return f"<{self.tagName}{attrs}>{''.join(map(str, self.data))}</{self.tagName}>"


class Element(HTMLElement):
    pass


class Console:
    def log(self, *a):
        _ = (self,)
        return print(*a)

    warn = error = debug = info = log


class Document:
    el_cls = Element

    head = el_cls('head')
    body = el_cls('body')

    title = 'BeePy'

    def createElement(self, tag_name):
        return self.el_cls(tag_name)

    querySelector = createElement

    def createDocumentFragment(self):
        return self.createElement('-')


class Location:
    pathname = '/e/'  # must be dynamic
    href = f'http://localhost:9000/{pathname}'
    search = ''
    hash = ''


class History:
    args = ()
    length = 0
    state = {}

    def pushState(self, state, unused, href):
        self.state = state
        self.args = (state, unused, href)

    replaceState = pushState  # We really don't care :)


class SearchParams:
    params = {}

    def get(self, name):
        return self.params.get(name)

    def set(self, name, value):
        self.params[name] = value


class URL:
    hash = '#'

    def __init__(self, href):
        self.href = href
        self.searchParams = SearchParams()

    @classmethod
    def new(cls, *a, **kw):
        return cls(*a, **kw)


class Object:
    @classmethod
    def keys(cls, obj):
        return obj.keys()

    @classmethod
    def fromEntries(cls, objs):
        return objs


class Event:
    def __init__(self, name):
        self.type = name


console = Console()
document = Document()
location = Location()
history = History()


async def delay(ms):
    time.sleep(ms)


class LocalStorage(dict):
    def getItem(self, key):
        return self[key]

    def setItem(self, key, value):
        self[key] = value

    def removeItem(self, key):
        del self[key]


localStorage = LocalStorage()


def decodeURI(text):
    return text


def decodeURIComponent(text):
    return text


def _DEBUGGER(error=None):
    print(error)


max_id = {'interval': 1, 'timeout': 1}
threads = {'interval': {}, 'timeout': {}}
listeners = defaultdict(lambda: defaultdict(list))
intervals = {}


def _js_func(fn):
    fn.name = fn.__qualname__
    return fn


@_js_func
def addEventListener(element, name, proxy):
    listeners[element][name].append(proxy)


@_js_func
def removeEventListener(element, name, proxy):
    listeners[element][name].remove(proxy)


@_js_func
def setInterval(callback, ms):
    def interval():
        while True:
            time.sleep(ms / 1000)
            callback()

    id = max_id['interval']
    max_id['interval'] += 1

    threads['interval'][id] = t = Thread(target=interval, daemon=True)
    t.start()


@_js_func
def clearInterval(interval_id):
    if interval_id in threads['interval']:
        threads['interval'][interval_id].join()


@_js_func
def setTimeout(callback, ms):
    def timeout():
        time.sleep(ms / 1000)
        callback()

    id = max_id['timeout']
    max_id['timeout'] += 1

    threads['timeout'][id] = t = Thread(target=timeout, daemon=True)
    t.start()


@_js_func
def clearTimeout(timeout_id):
    if timeout_id in threads['timeout']:
        threads['timeout'][timeout_id].join()


if TYPE_CHECKING:
    from beepy.framework import Tag


class BeePyModule:
    config = {}

    def addElement(self, mount_point, element_name, **options):
        return HTMLElement(element_name, _parent=mount_point)

    def startLoading(self, *a, **kw):
        return

    def stopLoading(self):
        return

    def addAsyncListener(self, el, eventName, method, modifiers, **options):
        return

    class files:
        _lastLoadedFile = ''

        @staticmethod
        def getPathWithCurrentPathAndOrigin(path):
            return path

    class dev_server:
        started = True


beepy = BeePyModule()
_locals = {}
window = self = globalThis = Self


# Mock of pyodide functions, but without `.destroy()`
# For testing outside of browser

#################
#       .       #
#       .       #
# . . . . . . . #
#       .       #
#       .       #
#################


EVENT_LISTENERS = {}


def add_event_listener(elt, event, listener):
    """Wrapper for JavaScript's addEventListener() which automatically manages the lifetime
    of a JsProxy corresponding to the listener param.
    """
    proxy = create_proxy(listener)
    EVENT_LISTENERS[(elt.js_id, event, listener)] = proxy
    elt.addEventListener(event, proxy)


def remove_event_listener(elt, event, listener):
    """Wrapper for JavaScript's removeEventListener() which automatically manages the lifetime
    of a JsProxy corresponding to the listener param.
    """
    elt.removeEventListener(event, EVENT_LISTENERS.pop((elt.js_id, event, listener)))


TIMEOUTS: dict[int, Callable] = {}


def set_timeout(callback, timeout):
    """Wrapper for JavaScript's setTimeout() which automatically manages the lifetime
    of a JsProxy corresponding to the callback param.
    """
    id = -1

    def wrapper():
        callback()
        TIMEOUTS.pop(id, None)

    callable = create_once_callable(wrapper)
    id = setTimeout(callable, timeout)
    TIMEOUTS[id] = callable
    return id


def clear_timeout(id):
    """Wrapper for JavaScript's clearTimeout() which automatically manages the lifetime
    of a JsProxy corresponding to the callback param.
    """
    clearTimeout(id)
    TIMEOUTS.pop(id, None)


INTERVAL_CALLBACKS: dict[int, Callable] = {}


def set_interval(callback, interval):
    """Wrapper for JavaScript's setInterval() which automatically manages the lifetime
    of a JsProxy corresponding to the callback param.
    """
    proxy = create_proxy(callback)
    id = setInterval(proxy, interval)
    INTERVAL_CALLBACKS[id] = proxy
    return id


def clear_interval(id):
    """Wrapper for JavaScript's clearInterval() which automatically manages the lifetime
    of a JsProxy corresponding to the callback param.
    """
    clearInterval(id)
    INTERVAL_CALLBACKS.pop(id, None)
