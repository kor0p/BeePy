from __future__ import annotations

import keyword
from collections import defaultdict
from typing import TYPE_CHECKING, Any, get_type_hints

from boltons.iterutils import first
from boltons.typeutils import issubclass

from beepy.types import AttrType, AttrValue
from beepy.utils import log
from beepy.utils.common import NONE_TYPE, call_handler_with_optional_arguments, to_kebab_case, wraps_with_name

if TYPE_CHECKING:
    import builtins
    from collections.abc import Callable, Sequence
    from typing import TypeVar

    from beepy.components import Component
    from beepy.context import Context

    T = TypeVar('T')

SPECIAL_CONVERT_ATTRIBUTES = {
    'contenteditable': lambda tag, val: (
        convert_boolean_attribute_value(val) if val == tag.mount_element.isContentEditable else val
    )
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


class attr:
    __slots__ = (
        'name',
        '_initial_value',
        'type',
        'const',
        'required',
        'notify',
        'static',
        'move_on',
        'model',
        'model_options',
        '_from_model_cache',
        'fget',
        'fset',
        'fdel',
        'handlers',
        'enum',
        '_cache',
    )

    _view = True
    _set_on_render = False

    name: str | None
    _initial_value: T
    type: builtins.type | None
    const: bool
    required: bool
    notify: bool
    static: bool
    move_on: bool
    model: str | None
    model_options: dict[str, Any]
    _from_model_cache: list[tuple[Component, attr, str | None]]
    fget: Callable[[Component], T]
    fset: Callable[[Component, T], None]
    fdel: Callable[[Component], None]
    handlers: dict[str, list[Callable[[Component, T], None]]]
    enum: Sequence

    _cache: dict[Component, AttrType]

    def __init__(  # noqa: PLR0913    # TODO: think about splitting logic
        self,
        default=None,
        *,
        const=False,
        required=False,
        notify=False,
        static=False,
        move_on=False,
        model=None,
        model_options=None,
        fget=None,
        fset=None,
        fdel=None,
        enum=None,
        **kwargs,
    ):
        _type = kwargs.get('type')

        self.name = None
        self.const = const
        assert not const or default is None, f'Const {type(self).__name__} cannot have initial value'
        self._initial_value = default
        self.required = required or const  # const attr must be also required
        self.notify = notify
        self.static = static
        self.move_on = move_on
        self.model = 'change' if model is True else model
        self.model_options = {'attribute': None} | (model_options or {})
        self._from_model_cache = []

        if default is None and _type is None:
            self.type = NONE_TYPE
        else:
            if _type is None:
                _type = default.type if self.model and isinstance(default, attr) else type(default)
            self._set_type(_type)

        # TODO: think on: is this needed?
        # behaviour like @property
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if fget:
            self(fget)

        self.handlers = defaultdict(list)
        self.enum = enum

        self._cache = {}

    @property
    def _priority(self):
        if self.move_on:
            return 0
        elif self.model:
            return 2
        else:
            return 1

    @classmethod
    def _order_dict_by_priority(cls, dict_attrs):
        return dict(sorted(dict_attrs.items(), key=lambda item: item[1]._priority))

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return (self.fget or self._fget)(instance)

    def _fget(self, instance):
        return self._cache.get(None if self.static else instance, self._initial_value)

    def __call__(self, fget):
        self.fget = fget
        self.name = to_kebab_case(fget.__name__)
        if self.type is NONE_TYPE:
            type_hints = get_type_hints(fget)
            if 'return' in type_hints:
                self._set_type(type_hints['return'])
        return self

    def __set__(self, instance, value, *, _prevent_model=False):
        current_value = self.__get__(instance)
        if self.const and current_value is not None:
            raise AttributeError

        if current_value == value:
            return

        (self.fset or self._fset)(instance, value)

        if instance._parent_ is not None:
            for handler in self.handlers['change']:
                if _prevent_model and _prevent_model in (True, self) and handler.__name__.startswith('@attr'):
                    continue
                call_handler_with_optional_arguments(handler, instance, {'value': value})

        if self.notify:
            instance.__notify__(self.name, self, value)

    def _set_first_value(self, instance, value, parent):  # noqa: ARG002 - unused `parent
        if self.model and (
            isinstance(value, attr) and value.name is not None and (instance, self, None) not in value._from_model_cache
        ):
            value._from_model_cache.append((instance, self, value.name))
            instance._kwargs.pop(self.name)

    def _fset(self, instance, value):
        if self.fget is not None:
            raise AttributeError

        if self.enum is not None and value not in self.enum:
            raise TypeError(f'Possible values: {self.enum}. Provided value: {value}')

        self._cache[None if self.static else instance] = value

    def setter(self, fset):
        self.fset = fset
        if self.type is NONE_TYPE:
            self._set_type(first(get_type_hints(fset).values()))
        return self

    def __set_name__(self, owner, name):
        if self._view:
            self.name = to_kebab_case(name)
        else:
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
            log.debug(
                f'Got error when trying to empty-args constructor of {self.type}: {e}\n'
                f'Will be better to set {self.name} not to None'
            )

    def _prepare_attribute_for_model(self, instance):
        if attribute := self.model_options['attribute']:
            if callable(attribute):
                return attribute(instance)
            return attribute

    def _set_model_value(self, instance, attr_, component: Component):
        initial_value = self.__get__(instance.parent if instance._parent_ is not None else component)

        if initial_value is None:
            if self._initial_value is not None:
                initial_value = self._initial_value
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
        return (self.fdel or self._fdel)(instance)

    def _fdel(self, instance):
        if self.fget is not None:
            raise AttributeError
        if self.static:
            return

        self._cache.pop(instance, None)

    def deleter(self, fdel):
        self.fdel = fdel
        return self

    def __repr__(self):
        return (
            f'{self.name} = {type(self).__name__}'
            f'(default={self._initial_value!r}, type={self.type}, static={self.static})'
        )

    def __str__(self):
        return f'{self.name}({self._initial_value!r})'

    def on(self, *triggers):
        def wrapper(handler):
            if self.static or self._from_model_cache:  # check if _from_model_cache is required
                if not hasattr(handler, '_attrs_static_'):
                    handler._attrs_static_ = defaultdict(list)
                for trigger in triggers:
                    handler._attrs_static_[trigger].append(self)

            for trigger in triggers:
                if handler in self.handlers[trigger]:
                    raise AttributeError(f"This @on('{trigger}') handler is already set")
            for trigger in triggers:
                self.handlers[trigger].append(handler)
            return handler

        return wrapper

    def _get_view_value(self, instance=None, value=None):
        if instance is not None:
            if value is not None:
                raise ValueError('You cannot provide both instance and value arguments')
            value = self.__get__(instance)

        if check_fn := SPECIAL_CONVERT_ATTRIBUTES.get(self.name):
            return check_fn(instance, value)

        if issubclass(self.type, bool):
            return convert_boolean_attribute_value(value)

        # support for custom types for attr
        if isinstance(self.type, AttrValue):
            return value.__view_value__()

        return value


class state(attr):
    __slots__ = ()

    _view = False


class html_attr(attr):
    __slots__ = ()

    _set_on_render = True

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


__all__ = ['attr', 'state', 'html_attr']
