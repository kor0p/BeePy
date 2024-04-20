from __future__ import annotations

from collections import defaultdict
from functools import partial
from types import MethodType
from typing import TYPE_CHECKING, Any, Self

import beepy
from beepy.attrs import set_html_attribute, state
from beepy.context import Context, _MetaContext
from beepy.listeners import on
from beepy.types import AttrType, Renderer, WebBase
from beepy.utils import IN_BROWSER, js
from beepy.utils.common import NONE_TYPE, nested_copy
from beepy.utils.dev import _debugger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from beepy.children import ComponentRef
    from beepy.framework import Tag


class LifecycleMethod:
    __slots__ = ('original_fn', 'steps', 'manager_fn', 'instance')

    original_fn: Callable
    steps: Iterable[str]
    manager_fn: Callable[[Component, str, tuple, dict], Any] | None
    instance: Component | None

    def __init__(self, original_fn, steps=(), manager_fn=None):
        self.original_fn = original_fn
        self.steps = steps
        self.manager_fn = manager_fn
        self.instance = None

    def call_as_super(self, this, args, kwargs):
        # This allows to call super()._method_() as usual function, not generator-function
        # So it skips calling manager, but function is called fully, as expected
        for _ in self.original_fn(this, *args, **kwargs):
            pass

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self._with_instance(instance)

    def _with_instance(self, instance):
        this = type(self)(self.original_fn, self.steps, self.manager_fn)
        this.instance = instance
        return this

    def _inherit(self, override_fn):
        this = type(self)(override_fn, self.steps, self.manager_fn)
        this.instance = self.instance
        return this

    def manager(self, steps: Iterable[str]):
        if self.manager_fn is not None:
            raise ValueError('Manager function is already set')

        self.steps = steps

        wrapper: Callable[[Component, str, tuple, dict], Any]

        def wrapper(fn):
            self.manager_fn = fn
            return fn

        return wrapper

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            raise ValueError("You can't call hook as class method")

        gen = self.original_fn(self.instance, *args, **kwargs)
        result = None

        while True:
            try:
                step = gen.send(result)
            except StopIteration:
                break

            if step in self.steps:
                result = self.manager_fn(self.instance, step, args, kwargs)
            else:
                raise ValueError(f'Invalid lifecycle step found: {step}. Available steps: {self.steps}')


_component_initialized = False


class _MetaComponent(_MetaContext):
    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):
        initialized = _component_initialized  # As base classes is also declared here, we must be sure base class exists

        static_onchange_handlers = []
        _lifecycle_methods = []

        base_cls: type[Component] | type = type.__new__(mcs, _name, bases, {})

        for _attribute_name, child in tuple(mcs._clean_namespace(namespace)):
            if isinstance(child, LifecycleMethod):
                _lifecycle_methods.append(child.original_fn.__name__)

            if initialized and callable(child) and hasattr(child, '_attrs_static_'):
                _states_with_static_handler = defaultdict(list)
                for trigger, _states in child._attrs_static_.items():
                    for _state in _states:
                        _states_with_static_handler[trigger].append(_state)
                        _state.handlers[trigger].remove(child)
                static_onchange_handlers.append((child, _states_with_static_handler))

        if initialized:
            for method_name in base_cls._lifecycle_methods:
                if method := namespace.get(method_name):
                    # TO THINK: Maybe create base class "AutoInherit" with "_inherit" method?
                    namespace[method_name] = getattr(base_cls, method_name)._inherit(method)

        cls: type[Component] | type = super().__new__(mcs, _name, bases, namespace, **kwargs)

        if initialized:
            cls._static_listeners = defaultdict(list, **nested_copy(cls._static_listeners))
            cls._static_onchange_handlers = cls._static_onchange_handlers.copy() + static_onchange_handlers
            cls._lifecycle_methods = cls._lifecycle_methods.copy() + _lifecycle_methods
        else:
            cls._static_listeners = defaultdict(list)
            cls._static_onchange_handlers = []
            cls._lifecycle_methods = _lifecycle_methods

        if hasattr(cls, '__extra_attributes__'):
            cls.__extra_attributes__ = {
                key: value._as_child(None) if isinstance(value, Component) else value
                for key, value in cls.__extra_attributes__.items()
            }

        return cls


class Component(WebBase, Context, metaclass=_MetaComponent, _root=True):
    __slots__ = ('_parent_', '_event_listeners', '_dependents', '_listeners', '_handlers', '_ref')

    parent: Tag | None
    mount_element: js.HTMLElement | None

    _ref: ComponentRef | None
    _force_ref: bool

    _event_listeners: defaultdict[str, list[Callable[[js.Event], None]]]
    _static_listeners: defaultdict[str, list[on]]
    _dependents: list[Renderer]
    _listeners: defaultdict[str, list[on]]
    _handlers: defaultdict[str, list[Callable[[Tag, js.Event, str, Any], None]]]
    _static_onchange_handlers: list[tuple[Callable[[Tag, Any], Any], dict[str, list[state]]]]
    _lifecycle_methods: list[str]

    @LifecycleMethod
    def __mount__(self, *args, **kwargs):
        result = yield 'call'
        yield 'attrs'

        for name, attribute in self._states.items():
            if callable(attribute) and not isinstance(attribute, MethodType):
                setattr(self, name, MethodType(attribute, self.parent))

        self._post_mount_attrs()

        for event, listeners in self._listeners.items():
            for listener in listeners:
                self._event_listeners[event].append(listener._make_listener(event, self))

        for onchange_handler, _states_with_static_handler in self._static_onchange_handlers:
            for trigger, _states in _states_with_static_handler.items():
                for _state in _states:
                    # TODO: can we save order of triggers' call?
                    _state.handlers[trigger].append(MethodType(onchange_handler, self))

        yield 'post_call'

        return result

    @__mount__.manager(steps=('call', 'attrs', 'post_call'))
    def __manager_mount(self, step: str, args: tuple, kwargs: dict):
        match step:
            case 'call':
                return self._mount_(*args, **kwargs)
            case 'attrs':
                self._mount_attrs()
            case 'post_call':
                self.mount()

    @LifecycleMethod
    def __unmount__(self, *args, **kwargs):
        if IN_BROWSER:
            for event, event_listeners in self._event_listeners.items():
                for event_listener in event_listeners:
                    on._remove_listener(event, self, event_listener)

        yield 'pre_call'

        result = yield 'call'
        yield 'post_call'
        return result

    @__unmount__.manager(steps=('pre_call', 'call', 'post_call'))
    def __manager_unmount(self, step, args, kwargs):
        match step:
            case 'pre_call':
                self.unmount()
            case 'call':
                return self._unmount_(*args, **kwargs)
            case 'post_call':
                self.post_unmount()

    @LifecycleMethod
    def __render__(self, attrs: dict[str, AttrType] | None = None, *args, **kwargs):
        # TODO: maybe function 'render' could return some content, appended to args?
        yield 'pre_call'

        if attrs is None:
            attrs = {}

        for name, value in {**self._attrs_values, **attrs}.items():
            # TODO: optimize this - set only changed attributes

            type = _attr.type if (_attr := self.attrs.get(name)) else NONE_TYPE
            set_html_attribute(self.mount_element, name, value, type=type)

        yield 'post_call'
        yield 'call'

    @__render__.manager(steps=('pre_call', 'call', 'post_call'))
    def __manager_render(self, step, args, kwargs):
        match step:
            case 'pre_call':
                self.render()
            case 'post_call':
                self.post_render()
            case 'call':
                return self._render_(*args, **kwargs)

    @property
    def parent(self):
        if self._parent_ is None:
            _debugger("ValueError: Trying to get .parent, but it's undefined")
        return self._parent_

    @parent.setter
    def parent(self, v):
        self._parent_ = v

    def _as_child(self, parent: Tag | None, *, exists_ok=False):
        if self._ref:
            if exists_ok:
                self._set_ref(parent, self._ref)
                return self._ref
            else:
                raise TypeError(f'Component {self._context_name_} already is child')
        ref = beepy.children.ComponentRef(self)
        self._set_ref(parent, ref)
        return ref

    def _set_ref(self, parent: Tag | None, ref: ComponentRef):  # noqa: ARG002 - unused `parent
        self._ref = ref

    def _clone(self, parent=None) -> Self:
        clone = super()._clone(parent=parent)
        clone._listeners = defaultdict(list, **nested_copy(self._listeners))
        clone._handlers = defaultdict(list, **nested_copy(self._handlers))
        return clone

    def __new__(cls, *args, **kwargs: AttrType):
        self: Component = super().__new__(cls, *args, **kwargs)
        self._parent_ = None

        self._dependents = []
        self._listeners = defaultdict(list, **nested_copy(self._static_listeners))
        self._event_listeners = defaultdict(list)
        self._handlers = defaultdict(list)

        self._ref = None

        return self

    def _mount_(self, element, parent: Tag, index=None):  # noqa: ARG002 - unused `element`, `index`
        self.parent = parent
        self.pre_mount()

        self.init(*self._args, **(self._attrs_defaults | self._kwargs))

    def _mount_attrs(self):
        for attribute in self.attrs.values():
            attribute._mount_cmpt(self)

    def _post_mount_attrs(self):
        for attribute in self.attrs.values():
            attribute._post_mount_cmpt(self)

    def pre_mount(self):
        """empty method for easy override with code for run before mount"""

    def mount(self):
        """empty method for easy override with code for run after mount"""

    def _unmount_(self, element, parent, *, _unsafe=False):
        pass

    def unmount(self):
        """empty method for easy override with code for run before unmount"""

    def post_unmount(self):
        """empty method for easy override with code for run after unmount"""

    def _render_(self, *args, **kwargs):
        pass

    def render(self):
        """empty method for easy override with code for run before render"""

    def post_render(self):
        """empty method for easy override with code for run after render"""

    def on(self, method: Callable | str):
        if isinstance(method, str) and method.startswith(':'):  # TODO: maybe it could be useful in `class on()`?
            action = method[1:]

            def wrapper(handler, action_name=None):
                if action_name is None:
                    action_name = handler.__name__

                self._handlers[action_name].append(handler)
                return handler

            if action:
                return partial(wrapper, action_name=action)

            return wrapper

        def wrapper(callback: Callable):
            event_listener = on(method)(callback, child=self)
            event_name = event_listener._name or callback.__name__
            event_listener.__set_name__(self, event_name)
            self._listeners[event_name] = [*self._listeners[event_name].copy(), event_listener]
            return callback

        if not isinstance(method, str):
            return wrapper(method)

        return wrapper


_component_initialized = True


class Directive(Component, _root=True):
    _force_ref: bool = True

    element = state()

    @property
    def el(self):
        if self.element:
            return getattr(self.parent, self.element)
        return self.parent

    @property
    def mount_element(self):
        return self.parent.mount_element


__all__ = ['_MetaComponent', 'Component', 'Directive']
