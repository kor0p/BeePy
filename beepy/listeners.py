from __future__ import annotations

import inspect
from collections import defaultdict
from functools import partial, wraps
from types import MethodType
from typing import TYPE_CHECKING, Any

from beepy.utils import js
from beepy.utils.asyncio import ensure_async
from beepy.utils.common import nested_copy
from beepy.utils.dev import _debugger
from beepy.utils.internal import _PY_TAG_ATTRIBUTE
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
_event_before_call = {
    'prevent': 'preventDefault',
    'stop': 'stopPropagation',
    'stop_all': 'stopImmediatePropagation',
}
_key_codes = {
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


def key_code_check(key_codes, event):
    # TODO: check for visibility?
    return event.keyCode in key_codes


def event_before_call(modifier_name, event):
    getattr(event, modifier_name)()
    return True


_checks = (
    (_event_before_call, event_before_call),
    (_key_codes, key_code_check),
)


class on:
    __slots__ = ('name', 'callback', 'pass_event', 'child_restrict', 'modifiers', 'checks')

    name: str | None
    callback: Callable[[Component, ...], Any]
    pass_event: bool
    child_restrict: type[Component] | None
    modifiers: list[str]
    checks: list[Callable[[js.Event], bool]]

    def __init__(self, method):  # TODO: add 'mount' callbacks?
        self.child_restrict = None
        self.pass_event = True
        self.modifiers = []
        self.checks = []

        if not isinstance(method, str):
            self.name = None
            self(method)
            return

        if '.' not in method:
            self.name = method
            return

        self.name, *self.modifiers = method.split('.')
        for modifier in self.modifiers:
            for checks, cb in _checks:
                if modifier in checks:
                    self.checks.append(partial(cb, checks[modifier]))
                    break
            else:
                raise ValueError(f'Unknown event modifier ".{modifier}"!')

    def __call__(self, method, child=None):
        self.callback = method
        self.child_restrict = child

        sig = inspect.signature(method)
        self.pass_event = 'event' in sig.parameters
        return self

    def _get_cb_and_instance(self, cmpt):
        if (
            self.child_restrict
            and cmpt.parent_defined
            and (self.child_restrict == cmpt or (cmpt._ref and self.child_restrict == cmpt._ref.child))
        ):
            cmpt = cmpt.parent

        if isinstance(self.callback, MethodType):
            return self.callback, cmpt
        else:
            return MethodType(self.callback, cmpt), cmpt

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._get_cb_and_instance(instance)[0]

    async def _call(self, cmpt, event):
        for check in self.checks:
            if not check(event):
                return

        fn, cmpt = self._get_cb_and_instance(cmpt)

        # TODO: use relaxed_call, when implemented in Pyodide
        args = (event,) if self.pass_event else ()

        try:
            await ensure_async(fn(*args))
        except Exception as e:  # noqa: BLE001 - catching any bad user input :)
            _debugger(e)

        for dependent in cmpt._dependents:
            # TODO: move to other place
            dependent.__render__()

        getattr(event.currentTarget, _PY_TAG_ATTRIBUTE, cmpt).__render__()

    def _make_listener(self, event_name: str, cmpt: Component):
        @wraps(self.callback)
        async def _handler(event):
            return await self._call(cmpt, event)

        handler = create_proxy(_handler)
        listener = handler.callSyncifying.bind(handler)

        global_events.get(event_name, cmpt.mount_element).addEventListener(event_name, listener)
        return listener

    @classmethod
    def _remove_listener(cls, event_name: str, cmpt: Component, event_listener: Callable):
        global_events.get(event_name, cmpt.mount_element).removeEventListener(event_name, event_listener)

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self.name} event handler')

    def __delete__(self, instance):
        pass

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

        if self.child_restrict is None:
            owner._static_listeners = defaultdict(list, **nested_copy(owner._static_listeners))
            owner._static_listeners[self.name].append(self)

    def __repr__(self):
        return f'on_{self.name}({self.callback})'


__all__ = ['on']
