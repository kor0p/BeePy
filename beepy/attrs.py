from __future__ import annotations

import builtins
import keyword
from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING, Any, get_type_hints

from boltons.iterutils import first
from boltons.typeutils import issubclass

from beepy.types import AttrType, AttrValue
from beepy.utils import log
from beepy.utils.common import NONE_TYPE, call_handler_with_optional_arguments, to_kebab_case, wraps_with_name

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import TypeVar

    from beepy.components import Component
    from beepy.context import Context

    T = TypeVar('T')

_special_convert_attributes = {
    'contenteditable': lambda tag, val: (
        convert_boolean_attribute_value(val) if val == tag.mount_element.isContentEditable else val
    ),
}


def convert_boolean_attribute_value(value):
    return '' if value else None


def set_html_attribute(el, name: str, value, *, type: builtins.type = NONE_TYPE):
    if value is None:
        el.removeAttribute(name)
    elif name.endswith('_'):
        el.setAttribute(name[:-1], value)
    elif not hasattr(el, name) or issubclass(type, bool):
        el.setAttribute(name, value)
    else:
        setattr(el, name, value)


class state:
    __slots__ = (
        'name',
        'type',
        'required',
        'model',
        'model_opts',
        'handlers',
        'enum',
        '_default',
        '_from_model_cache',
        '_cache',
    )

    name: str | None
    type: builtins.type | None
    required: bool
    model: str | None
    model_opts: dict[str, Any]
    handlers: dict[str, list[Callable[[Component, T], None]]]
    enum: Sequence

    _default: T
    _from_model_cache: list[tuple[Component, state, str | None]]
    _cache: dict[Component, AttrType]

    def __init__(self, default=None, *, required=False, model=None, model_opts=None, enum=None, type=None):
        # TO THINK: add `const` (removed feature)

        self.name = None
        self._default = default
        self.required = required
        self.model = 'change' if model is True else model
        self.model_opts = {'attribute': None} | (model_opts or {})
        self._from_model_cache = []

        if default is None and type is None:
            self.type = NONE_TYPE
        else:
            if type is None:
                type = default.type if self.model and isinstance(default, state) else builtins.type(default)
            self._set_type(type)

        self.handlers = defaultdict(list)
        self.enum = enum

        self._cache = {}

    @property
    def _priority(self):
        return 2 if self.model else 1

    @classmethod
    def _order_dict_by_priority(cls, dict_attrs):
        return dict(sorted(dict_attrs.items(), key=lambda item: item[1]._priority))

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._fget(instance)

    def _fget(self, instance):
        return self._cache.get(instance, self._default)

    def __set__(self, instance, value, *, _prevent_model=False):
        current_value = self.__get__(instance)

        if current_value == value:
            return

        self._fset(instance, value)

        if instance._parent_ is not None:
            for handler in self.handlers['change']:
                if _prevent_model and _prevent_model in (True, self) and handler.__name__.startswith('@attr'):
                    continue
                call_handler_with_optional_arguments(handler, instance, {'value': value})

    def _set_first_value(self, instance, value, parent):  # noqa: ARG002 - unused `parent
        if self.model and (
            isinstance(value, state) and value.name and (instance, self, None) not in value._from_model_cache
        ):
            value._from_model_cache.append((instance, self, value.name))
            instance._kwargs.pop(self.name)

    def _fset(self, instance, value):
        if self.enum is not None and value not in self.enum:
            raise TypeError(f'Possible values: {self.enum}. Provided value: {value}')

        self._cache[instance] = value

    def __set_name__(self, owner, name):
        self.name = name

    def _set_type(self, _type, *, raise_error=False):
        if hasattr(_type, '__origin__'):  # TODO: add support of strict check of type on change/etc
            _type = _type.__origin__

        if not isinstance(_type, type):
            error = f'Bad type for attribute: {_type!r}, {type(_type)}'
            if raise_error:
                raise TypeError(error)
            else:
                self.type = NONE_TYPE
                return log.error(error)

        self.type = _type

    def _link_cmpt(self, name: str, component: Component, *, force: bool = True, force_cls_set: bool = False):
        component.attrs[name] = self
        if force:
            self.__set_name__(component, name)
        if force_cls_set:
            setattr(type(component), name, self)
        elif not hasattr(component, name) and hasattr(component, 'mount_element'):
            setattr(component, name, self.__get__(component))
        return self

    def _get_type_instance(self):
        try:
            return self.type()
        except Exception as e:  # noqa: BLE001 - trying to call empty constructor
            log.warn(
                f'Got error when trying to empty-args constructor of {self.type}: {e}\n'
                f'Will be better to set {self.name} not to None'
            )

    def _prepare_attribute_for_model(self, instance):
        if attribute := self.model_opts['attribute']:
            if callable(attribute):
                return attribute(instance)
            return attribute

    def _set_model_value(self, instance, attr_, component: Component):
        initial_value = self.__get__(instance.parent if instance._parent_ is not None else component)

        if initial_value is None:
            if self._default is not None:
                initial_value = self._default
            elif self.type and (value_from_type := self._get_type_instance()) is not None:
                initial_value = value_from_type
        if attribute_ := self._prepare_attribute_for_model(instance):
            initial_value = getattr(initial_value, attribute_)
        if initial_value is None:
            initial_value = ''

        attr_.__set__(instance, initial_value, _prevent_model=attribute_)

        return attribute_

    def _handle_model_listeners(self, component: Component):
        to_remove_indexes = []

        for index, (instance, attr_, name) in enumerate(self._from_model_cache):
            if name is None:
                to_remove_indexes.append(index)
                continue

            if instance._parent_ is not None and instance.parent != component:
                continue

            attribute_ = self._set_model_value(instance, attr_, component)

            _attribute_str = f'({attribute_})' if attribute_ else ''

            @instance.on(attr_.model)
            @wraps_with_name(f'@attr[to:{attr_}->model{_attribute_str}->{self}]')
            def __handler_to_model(parent_instance, event, current_attribute=attribute_):
                value = event.target.value
                if current_attribute:
                    setattr(self.__get__(parent_instance), current_attribute, value)
                else:
                    self.__set__(parent_instance, value, _prevent_model=current_attribute)

            @self.on('change')
            @wraps_with_name(f'@attr[from:{attr_}->model{_attribute_str}->{self}]')
            def __handler_from_model(
                parent_instance, value, current_instance=instance, _attr_=attr_, current_attribute=attribute_
            ):
                instance_ = getattr(parent_instance, current_attribute) if current_attribute else current_instance

                if value is not None and current_attribute:
                    value = getattr(value, current_attribute)

                _attr_.__set__(instance_, value, _prevent_model=current_attribute)

        for index in reversed(to_remove_indexes):
            self._from_model_cache.pop(index)

    def _init_ctx(self, ctx: Context, value):
        for handler in self.handlers['init']:
            call_handler_with_optional_arguments(handler, ctx, {'value': value})

    def _mount_cmpt(self, component: Component):
        self._handle_model_listeners(component)

    def _post_mount_cmpt(self, component: Component):
        for instance, attr_, _ in self._from_model_cache:
            self._set_model_value(instance, attr_, component)

        if self.handlers['mount']:
            value = self.__get__(component)
            for handler in self.handlers['mount']:
                call_handler_with_optional_arguments(handler, component, {'value': value})

    def __delete__(self, instance):
        return self._fdel(instance)

    def _fdel(self, instance):
        self._cache.pop(instance, None)

    def __repr__(self):
        return f'{self.name} = {type(self).__name__}(default={self._default!r}, type={self.type})'

    def __str__(self):
        return f'{self.name}({self._default!r})'

    def _on_wrapper(self, handler, *, triggers):
        for trigger in triggers:
            if handler in self.handlers[trigger]:
                raise AttributeError(f"This @on('{trigger}') handler is already set")
        for trigger in triggers:
            self.handlers[trigger].append(handler)
        return handler

    def on(self, *triggers):
        return partial(self._on_wrapper, triggers=triggers)

    def _get_view_value(self, instance=None, value=None):
        if instance is not None:
            if value is not None:
                raise ValueError('You cannot provide both instance and value arguments')
            value = self.__get__(instance)

        if check_fn := _special_convert_attributes.get(self.name):
            return check_fn(instance, value)

        if issubclass(self.type, bool):
            return convert_boolean_attribute_value(value)

        # support for custom types for attr
        if isinstance(self.type, AttrValue):
            return value.__view_value__()

        return value


class attr(state):
    __slots__ = ()

    def __set_name__(self, owner, name):
        self.name = to_kebab_case(name)


class state_move_on(state):
    __slots__ = ()

    _move_on = True
    _priority = 0


class attr_prop(attr):
    __slots__ = ('fget', 'fset', 'fdel')

    fget: Callable[[Component], T]
    fset: Callable[[Component, T], None]
    fdel: Callable[[Component], None]

    def __init__(self, *args, fget=None, fset=None, fdel=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if fget:
            self(fget)

    def _fget(self, instance):
        if self.fget is not None:
            return self.fget(instance)
        return super()._fget(instance)

    def __call__(self, fget):
        self.fget = fget
        self.name = to_kebab_case(fget.__name__)
        if self.type is NONE_TYPE:
            type_hints = get_type_hints(fget)
            if 'return' in type_hints:
                self._set_type(type_hints['return'])
        return self

    def _fset(self, instance, value):
        if self.fset is not None:
            return self.fset(instance, value)
        if self.fget is not None:
            raise AttributeError('This attr have no setter')
        return super()._fset(instance, value)

    def setter(self, fset):
        self.fset = fset
        if self.type is NONE_TYPE:
            self._set_type(first(get_type_hints(fset).values()))
        return self

    def _fdel(self, instance):
        if self.fdel is not None:
            return self.fdel(instance)
        if self.fget is not None:
            raise AttributeError('This attr have no deleter')
        return super()._fdel(instance)

    def deleter(self, fdel):
        self.fdel = fdel
        return self


class state_static(state):
    __slots__ = ()

    def _fget(self, instance):  # noqa: ARG002 - unused `instance`
        return super()._fget(None)

    def _fset(self, instance, value):  # noqa: ARG002 - unused `instance`
        super()._fset(None, value)

    def _fdel(self, instance):  # noqa: ARG002 - unused `instance`
        return  # Static state shouldn't be deleted by `__delete__`

    def clear(self):
        super()._fdel(None)

    def _on_wrapper(self, handler, *, triggers):
        if not hasattr(handler, '_attrs_static_'):
            handler._attrs_static_ = defaultdict(list)
        for trigger in triggers:
            handler._attrs_static_[trigger].append(self)

        return super()._on_wrapper(handler, triggers=triggers)


class html_attr(attr):
    __slots__ = ()

    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def __set_name__(self, owner, name):
        if self.name is None:
            super().__set_name__(owner, name)
        if self.name in keyword.kwlist:
            self.name += '_'

    def _fget(self, instance):
        if instance is None:
            return self

        el = instance.mount_element
        if hasattr(el, self.name):  # noqa: SIM108 - just want to see difference
            value = getattr(el, self.name, None)
        else:
            value = el.getAttribute(self.name)

        return (value == '') if issubclass(self.type, bool) else value

    def _fset(self, instance, value):
        if hasattr(instance, 'mount_element'):
            value = self._get_view_value(value=value)
            set_html_attribute(instance.mount_element, self.name, value, type=self.type)

    def _fdel(self, instance):
        delattr(instance.mount_element, self.name)


class listen_state(state):
    __slots__ = ('provider', 'subscribers')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = None
        self.subscribers = []

    def _mount_cmpt(self, component: Component):
        if self.provider is None:
            self.provider = component
        else:
            self.subscribers.append(component)

    def __set__(self, instance, value, *, _prevent_model=False):
        super().__set__(instance, value, _prevent_model=_prevent_model)
        if instance is self.provider:
            for component in self.subscribers:
                component.__notify__(self.name, self, value)


__all__ = ['state', 'attr', 'attr_prop', 'state_move_on', 'state_static', 'html_attr']
