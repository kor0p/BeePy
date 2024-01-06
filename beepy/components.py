from __future__ import annotations

import inspect
import traceback
from copy import deepcopy
from functools import partial, wraps
from types import MethodType
from typing import Any, Callable, Optional, Type, Union
from collections import defaultdict

from beepy.attrs import set_html_attribute, state
from beepy.children import ComponentRef
from beepy.context import _MetaContext, Context
from beepy.types import AttrType, Renderer, Tag, WebBase
from beepy.listeners import on
from beepy.utils import js, IN_BROWSER, log, to_js
from beepy.utils.common import NONE_TYPE

_current__lifecycle_method: dict[str, dict[int, Component]] = {}


def _lifecycle_method(*, hash_function=hash):
    def _wrapper(fn):
        name = fn.__name__
        attr_name = f'_wrapper_{name}_calling'
        _cache = _current__lifecycle_method[attr_name] = {}

        @wraps(fn)
        def lifecycle_method(original_func):
            @wraps(original_func)
            def original_method_wrapper(self, *args, **kwargs):
                # prevent calling super() calls extra code twice
                _hash = hash_function(self)
                not_in_super_call = _hash not in _cache

                if not_in_super_call:
                    _cache[_hash] = self
                    result = fn(self, args, kwargs, _original_func=original_func)
                    del _cache[_hash]
                else:
                    result = original_func(self, *args, **kwargs)

                return result
            return original_method_wrapper
        return lifecycle_method
    return _wrapper


_COMPONENT_INITIALIZED = False


class _MetaComponent(_MetaContext):
    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):
        initialized = _COMPONENT_INITIALIZED  # As base classes is also declared here, we must be sure base class exists

        static_onchange_handlers = []

        if initialized:
            for attribute_name, child in tuple(mcs._clean_namespace(namespace)):
                if not (callable(child) and hasattr(child, '_attrs_static_')):
                    continue

                _states_with_static_handler = defaultdict(list)
                for trigger, _states in child._attrs_static_.items():
                    for _state in _states:
                        _states_with_static_handler[trigger].append(_state)
                        _state.handlers[trigger].remove(child)
                static_onchange_handlers.append((child, _states_with_static_handler))

        cls: Union[Type[Component], type] = super().__new__(mcs, _name, bases, namespace, **kwargs)

        if initialized:
            cls._static_listeners = deepcopy(cls._static_listeners)
            cls._static_onchange_handlers = cls._static_onchange_handlers.copy() + static_onchange_handlers
        else:
            cls._static_listeners = defaultdict(list)
            cls._static_onchange_handlers = []

        if hasattr(cls, '__extra_attributes__'):
            cls.__extra_attributes__ = {
                key: value.as_child(None) if isinstance(value, Component) else value
                for key, value in cls.__extra_attributes__.items()
            }

        if '__mount__' in namespace:
            cls.__mount__ = mcs.__mount(cls.__mount__)

        if '__render__' in namespace:
            cls.__render__ = mcs.__render(cls.__render__)

        if '__init__' in namespace:
            cls.__init__ = mcs.__init(cls.__init__)

        if '__unmount__' in namespace:
            cls.__unmount__ = mcs.__unmount(cls.__unmount__)

        return cls

    @_lifecycle_method(hash_function=id)
    def __init(self: Component, args, kwargs, _original_func):
        return self.__class__.__META_init__(self, args, kwargs, _original_func)

    @_lifecycle_method()
    def __mount(self: Component, args, kwargs, _original_func):
        return self.__class__.__META_mount__(self, args, kwargs, _original_func)

    @_lifecycle_method()
    def __unmount(self: Component, args, kwargs, _original_func):
        return self.__class__.__META_unmount__(self, args, kwargs, _original_func)

    @_lifecycle_method()
    def __render(self: Component, args, kwargs, _original_func):
        return self.__class__.__META_render__(self, args, kwargs, _original_func)

    @classmethod
    def __META_init__(cls, self: Component, args, kwargs, _original_func):
        self._parent_ = None

        self._dependents = []
        self._listeners = deepcopy(self._static_listeners)
        self._event_listeners = defaultdict(list)
        self._handlers = defaultdict(list)

        self._ref = None

        _original_func(self, *args, **kwargs)

    @classmethod
    def __META_mount__(cls, self: Component, args, kwargs, _original_func, _mount_attrs=True):
        result = _original_func(self, *args, **kwargs) if _original_func else None

        if _mount_attrs:
            self._mount_attrs()

        for name, attribute in self.__states__.items():
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

        self.mount()

        return result

    @classmethod
    def __META_unmount__(cls, self: Component, args, kwargs, _original_func, _post_mount=True):
        if not _post_mount:
            self.unmount()

        result = _original_func(self, *args, **kwargs) if _original_func else None

        if IN_BROWSER:
            for event, event_listeners in self._event_listeners.items():
                for event_listener in event_listeners:
                    on._remove_listener(event, self, event_listener)

        if _post_mount:
            self.unmount()

        return result

    @classmethod
    def __META_render__(cls, self: Component, args, kwargs, _original_func):
        # TODO: maybe function 'render' could return some content, appended to args?
        self.render()

        attrs: dict[str, AttrType] = args[0] if len(args) > 0 else {}

        for name, value in {**self.__attrs__, **attrs}.items():
            # TODO: optimize this - set only changed attributes

            if _attr := self.attrs.get(name):
                type = _attr.type
            else:
                type = NONE_TYPE
            set_html_attribute(self.mount_element, name, value, type=type)

        self.post_render()

        _original_func(self, *args, **kwargs)


class Component(WebBase, Context, metaclass=_MetaComponent, _root=True):
    __slots__ = ('_parent_', '_event_listeners', '_dependents', '_listeners', '_handlers', '_ref')

    parent: Optional[Tag]

    _ref: Optional[ComponentRef]
    _force_ref: bool

    _event_listeners: defaultdict[str, list[Callable[[js.Event], None]]]
    _static_listeners: defaultdict[str, list[on]]
    _dependents: list[Renderer]
    _listeners: defaultdict[str, list[on]]
    _handlers: defaultdict[str, list[Callable[[Tag, js.Event, str, Any], None]]]
    _static_onchange_handlers: list[tuple[Callable[[Tag, Any], Any], dict[str, list[state]]]]

    @property
    def parent_defined(self):
        return self._parent_ is not None

    @property
    def parent(self):
        if self._parent_ is None:
            try:
                raise ValueError
            except ValueError:
                frame = inspect.currentframe().f_back
                log.warn(traceback.format_exc(), inspect.getsourcefile(frame), frame.f_lineno, to_js(frame.f_locals))
        return self._parent_

    @parent.setter
    def parent(self, v):
        self._parent_ = v

    def as_child(self, parent: Optional[Tag], exists_ok=False):
        if self._ref:
            if exists_ok:
                self.__set_ref__(parent, self._ref)
                return self._ref
            else:
                raise TypeError(f'Component {self._context_name_} already is child')
        ref = ComponentRef(self)
        self.__set_ref__(parent, ref)
        return ref

    def __set_ref__(self, parent: Optional[Tag], ref: ComponentRef):
        self._ref = ref

    def clone(self, parent=None) -> Component:
        clone = super().clone(parent=parent)
        clone._listeners = deepcopy(self._listeners)
        clone._handlers = deepcopy(self._handlers)
        return clone

    def __init__(self, *args, **kwargs: AttrType):
        # DO NOT DELETE; This method must be wrapped by _MetaTag.__init
        super().__init__(*args, **kwargs)

    def __mount__(self, element, parent: Tag, index=None):
        self.parent = parent
        self.pre_mount()

        args, kwargs = self.args_kwargs
        kwargs = self._attrs_defaults | kwargs
        self.init(*args, **kwargs)

    def _mount_attrs(self):
        for attribute in self.attrs.values():
            attribute.__mount_ctx__(self)

    def _post_mount_attrs(self):
        for attribute in self.attrs.values():
            attribute.__post_mount_ctx__(self)

    def pre_mount(self):
        """empty method for easy override with code for run before mount"""

    def mount(self):
        """empty method for easy override with code for run after mount"""

    def unmount(self):
        """empty method for easy override with code for run before unmount"""

    def post_unmount(self):
        """empty method for easy override with code for run after unmount"""

    def render(self):
        """empty method for easy override with code for run before render"""

    def post_render(self):
        """empty method for easy override with code for run after render"""

    def on(self, method: Union[Tag, str]):
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

        def wrapper(callback):
            event_listener = on(method)(callback, get_parent=True)
            event_name = event_listener.name or callback.__name__
            event_listener.__set_name__(self, event_name, set_static_listeners=False)
            self._listeners[event_name] = self._listeners[event_name].copy() + [event_listener]
            return event_listener.__get__(self)

        if not isinstance(method, str):
            return wrapper(method)

        return wrapper


_COMPONENT_INITIALIZED = True


class Directive(Component, _root=True):
    _force_ref: bool = True

    element = state()

    def __unmount__(self, element, parent, _unsafe=False):
        # DO NOT DELETE; This method must be wrapped by _MetaTag.__unmount
        pass

    def __render__(self):
        # DO NOT DELETE; This method must be wrapped by _MetaTag.__render
        pass

    @property
    def el(self):
        if self.element:
            return getattr(self.parent, self.element)
        return self.parent

    @property
    def mount_element(self):
        return self.parent.mount_element


__all__ = ['_MetaComponent', 'Component', 'Directive']
