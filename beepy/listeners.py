from __future__ import annotations

import inspect
from collections import defaultdict
from functools import partial, wraps
from types import MethodType
from typing import TYPE_CHECKING, Any

from beepy.utils import js, to_js
from beepy.utils.common import nested_copy
from beepy.utils.internal import _py_tag_attribute
from beepy.utils.js_py import create_proxy

if TYPE_CHECKING:
    from collections.abc import Callable

    from beepy.components import Component

global_events = {
    'keyup': js.document,
    'keypress': js.document,
    'keydown': js.document,
    'popstate': js.window,
    'hashchange': js.window,
}
_key_codes = {
    # TODO: add all symbols and support raw keyCodes
    'esc': (27,),
    'tab': (9,),
    'enter': (13,),
    'space': (32,),
    'up': (38,),
    'left': (37,),
    'right': (39,),
    'down': (40,),
    'delete': (8, 46),
}


# TODO: click.(right|middle) ; click.left ; etc.


def key_code_check(key_name, event):
    return event.keyCode in _key_codes[key_name]


_raw_js_checks = ('prevent', 'stop', 'stop_all')


class on:
    __slots__ = ('_name', '_callback', '_pass_event', '_child_restrict', '_modifiers', '_checks', '_js_checks')

    _name: str | None
    _callback: Callable[[Component, ...], Any]
    _pass_event: bool
    _child_restrict: type[Component] | None
    _modifiers: list[str]
    _checks: list[Callable[[js.Event], bool]]
    _js_checks: list[str]

    def __init__(self, method):  # TODO: add 'mount' callbacks?
        self._child_restrict = None
        self._pass_event = True
        self._modifiers = []
        self._checks = []
        self._js_checks = []

        if not isinstance(method, str):
            self._name = None
            self(method)
            return

        if '.' not in method:
            self._name = method
            return

        self._name, *self._modifiers = method.split('.')
        for modifier in self._modifiers:
            if modifier in _key_codes:
                # TODO: check for visibility?
                self._checks.append(partial(key_code_check, modifier))
            elif modifier in _raw_js_checks:
                self._js_checks.append(modifier)
            else:
                raise ValueError(f'Unknown event modifier ".{modifier}"!')

    def __call__(self, method, child=None):
        self._callback = method
        self._child_restrict = child

        sig = inspect.signature(method)
        self._pass_event = 'event' in sig.parameters
        return self

    def _get_cb_and_instance(self, cmpt):
        if (
            self._child_restrict
            and cmpt._parent_ is not None
            and (self._child_restrict == cmpt or (cmpt._ref and self._child_restrict == cmpt._ref.child))
        ):
            cmpt = cmpt.parent

        if isinstance(self._callback, MethodType):
            return self._callback, cmpt
        else:
            return MethodType(self._callback, cmpt), cmpt

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._get_cb_and_instance(instance)[0]

    def _prepare_call(self, cmpt, event):
        for check in self._checks:
            if not check(event):
                return

        return self._get_cb_and_instance(cmpt)

    async def _a_call(self, cmpt, event):
        if (prepare := self._prepare_call(cmpt, event)) is None:
            return

        fn, cmpt = prepare

        args = (event,) if self._pass_event else ()
        data = await fn(*args)
        self._after_call(cmpt, event)
        return data

    def _call(self, cmpt, event):
        if (prepare := self._prepare_call(cmpt, event)) is None:
            return

        fn, cmpt = prepare
        args = (event,) if self._pass_event else ()
        data = fn(*args)
        self._after_call(cmpt, event)
        return data

    def _after_call(self, cmpt, event):
        for dependent in cmpt._dependents:
            # TODO: move to other place
            dependent.__render__()

        getattr(event.currentTarget, _py_tag_attribute, cmpt).__render__()

    def _make_listener(self, event_name: str, cmpt: Component):
        if inspect.iscoroutinefunction(self._callback):

            @wraps(self._callback)
            async def method(event):
                return await self._a_call(cmpt, event)

        else:

            @wraps(self._callback)
            def method(event):
                return self._call(cmpt, event)

        return js.beepy.addAsyncListener(
            global_events.get(event_name, cmpt.mount_element), event_name, create_proxy(method), to_js(self._js_checks)
        )

    @classmethod
    def _remove_listener(cls, event_name: str, cmpt: Component, event_listener: Callable):
        global_events.get(event_name, cmpt.mount_element).removeEventListener(event_name, event_listener)

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self._name} event handler')

    def __delete__(self, instance):
        pass

    def __set_name__(self, owner, name):
        if self._name is None:
            self._name = name

        if self._child_restrict is None:
            owner._static_listeners = defaultdict(list, **nested_copy(owner._static_listeners))
            owner._static_listeners[self._name].append(self)

    def __repr__(self):
        return f'on_{self._name}({self._callback})'


__all__ = ['on']
