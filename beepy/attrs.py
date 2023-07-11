from __future__ import annotations as _

import builtins
import keyword
from typing import Optional, Callable, Union, Sequence, Type, get_type_hints, ForwardRef, TypeVar, Any
from collections import defaultdict

from beepy.types import AttrType, AttrValue
from beepy.utils.common import NONE_TYPE, wraps_with_name, to_kebab_case
from beepy.utils import log


Context = ForwardRef('Context')
T = TypeVar('T')

SPECIAL_CONVERT_ATTRIBUTES = {
    'contenteditable': lambda tag, val: (
        convert_boolean_attribute_value(val) if val == tag.mount_element.isContentEditable else val
    ),
}


def convert_boolean_attribute_value(value):
    return '' if value else None


_MISSING = object()


def set_html_attribute(el, name: str, value, *, type: builtins.type = NONE_TYPE):
    existing_attribute = getattr(el, name, _MISSING)
    if value is None:
        el.removeAttribute(name)
    elif name.endswith('_'):
        el.setAttribute(name[:-1], value)
    elif existing_attribute is _MISSING or issubclass(type, bool):
        el.setAttribute(name, value)
    else:
        setattr(el, name, value)


class attr:
    __slots__ = (
        'name', 'initial_value', 'type',
        'const', 'required', 'notify',
        'static', 'move_on', 'model',
        'model_options', '_from_model_cache',
        'fget', 'fset', 'fdel',
        'handlers',
        'enum',
        '_cache',
    )

    _view = True
    _set_on_render = False

    name: Optional[str]
    initial_value: T
    type: Optional[Union[type, Type[Context]]]
    const: bool
    required: bool
    notify: bool
    static: bool
    move_on: bool
    model: Optional[str]
    model_options: dict[str, Any]
    _from_model_cache: list[tuple[Context, attr, Optional[str]]]
    fget: Callable[[Context], T]
    fset: Callable[[Context, T], None]
    fdel: Callable[[Context], None]
    handlers: dict[str, list[Callable[[Context, T], None]]]
    enum: Sequence

    _cache: dict[Context, AttrType]

    def __init__(
        self, initial_value=None, /, *,
        const=False, required=False, notify=False,
        static=False, move_on=False, model=None, model_options=None,
        fget=None, fset=None, fdel=None,
        enum=None,
        **kwargs,
    ):
        _type = kwargs.get('type')

        self.name = None
        self.const = const
        assert not const or initial_value is None, f'Const {type(self).__name__} cannot have initial value'
        self.initial_value = initial_value
        self.required = required or const  # const attr must be also required
        self.notify = notify
        self.static = static
        self.move_on = move_on
        self.model = 'change' if model is True else model
        self.model_options = {'attribute': None} | (model_options or {})
        self._from_model_cache = []

        if initial_value is None and _type is None:
            self.type = NONE_TYPE
        else:
            if _type is None:
                if self.model and isinstance(initial_value, attr):
                    _type = initial_value.type
                else:
                    _type = type(initial_value)
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
    def priority(self):
        if self.move_on:
            return 0
        elif self.model:
            return 2
        else:
            return 1

    @classmethod
    def order_dict_by_priority(cls, dict_attrs):
        return dict(sorted(dict_attrs.items(), key=lambda item: item[1].priority))

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return (self.fget or self._fget)(instance)

    def _fget(self, instance):
        return self._cache.get(None if self.static else instance, self.initial_value)

    def __call__(self, fget):
        self.fget = fget
        self.name = to_kebab_case(fget.__name__)
        if self.type is NONE_TYPE:
            annotations = get_type_hints(fget)
            if 'return' in annotations:
                self._set_type(annotations['return'])
        return self

    def __set__(self, instance, value, _prevent_model=False):
        current_value = self.__get__(instance)
        if self.const and current_value is not None:
            raise AttributeError

        if current_value == value:
            return

        (self.fset or self._fset)(instance, value)

        for trigger in self.handlers['change']:
            if _prevent_model and trigger.__name__.startswith('@attr'):
                continue
            trigger(instance, value)

        if self.notify:
            instance.__notify__(self.name, self, value)

    def __set_first__(self, instance, value, parent):
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
            self._set_type(tuple(get_type_hints(fset).values())[0])
        return self

    def __set_name__(self, owner, name):
        if self._view:
            self.name = to_kebab_case(name)
        else:
            self.name = name

    def _set_type(self, _type, raise_error=False):
        if hasattr(_type, '__origin__'):  # TODO: add support of strict check of type on change/etc
            _type = _type.__origin__
        try:
            issubclass(_type, type)
        except TypeError as e:
            error = f'Bad type for attribute: {_type!r}, {type(_type)}'
            if raise_error:
                raise TypeError(error) from e
            else:
                self.type = NONE_TYPE
                return log.error(error)

        self.type = _type

    def _link_ctx(self, name: str, ctx: Context, force: bool = True, force_cls_set: bool = False):
        ctx.attrs[name] = self
        if force:
            self.__set_name__(ctx, name)
        if force_cls_set:
            setattr(type(ctx), name, self)
        elif not hasattr(ctx, name) and hasattr(ctx, 'mount_element'):
            setattr(ctx, name, self.__get__(ctx))
        return self

    def _get_type_instance(self, *, error_text=''):
        try:
            return self.type()
        except Exception as e:
            log.debug(f'Got error when trying to empty-args constructor of {self.type}: {e}\n' + error_text)

    def _prepare_attribute_for_model(self, instance):
        if attribute := self.model_options['attribute']:
            if callable(attribute):
                return attribute(instance)
            return attribute

    def _set_model_value(self, instance, attr_, ctx: Context):
        value = self.__get__(instance.parent if instance.parent_defined else ctx)

        if value is None:
            if self.initial_value is not None:
                value = self.initial_value
            elif self.type:
                __value = self._get_type_instance(error_text=f'Will be better to set {self.name} not to None')
                if __value is not None:
                    value = __value
        if attribute_ := self._prepare_attribute_for_model(instance):
            value = getattr(value, attribute_)
        if value is None:
            value = ''

        attr_.__set__(instance, value, _prevent_model=True)

        return attribute_

    def _handle_model_listeners(self, ctx: Context):
        to_remove_indexes = []

        for index, (instance, attr_, name) in enumerate(self._from_model_cache):
            if name is None:
                to_remove_indexes.append(index)
                continue

            if instance.parent_defined and instance.parent != ctx:
                continue

            attribute_ = self._set_model_value(instance, attr_, ctx)

            _attribute_str = f'({attribute_})' if attribute_ else ''

            @instance.on(attr_.model)
            @wraps_with_name(f'@attr[to:{attr_}->model{_attribute_str}->{self}]')
            def __handler_to_model(parent_instance, _event, current_attribute=attribute_):
                _value = _event.target.value
                if current_attribute:
                    setattr(self.__get__(parent_instance), current_attribute, _value)
                else:
                    self.__set__(parent_instance, _value, _prevent_model=True)

            @self.on('change')
            @wraps_with_name(f'@attr[from:{attr_}->model{_attribute_str}->{self}]')
            def __handler_from_model(
                parent_instance, _value, current_instance=instance, _attr_=attr_, current_attribute=attribute_
            ):
                instance_ = getattr(parent_instance, current_attribute) if current_attribute else current_instance

                if _value is not None and current_attribute:
                    _value = getattr(_value, current_attribute)

                _attr_.__set__(instance_, _value, _prevent_model=True)

        for index in reversed(to_remove_indexes):
            self._from_model_cache.pop(index)

    def __mount_tag__(self, ctx: Context):
        self._handle_model_listeners(ctx)

    def __post_mount_tag__(self, ctx: Context):
        for instance, attr_, _ in self._from_model_cache:
            self._set_model_value(instance, attr_, ctx)

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
            f'(default={self.initial_value!r}, type={self.type}, static={self.static})'
        )

    def __str__(self):
        return f'{self.name}({self.initial_value!r})'

    def on(self, trigger):
        def wrapper(handler):
            if self.static or self._from_model_cache:  # check if _from_model_cache is required
                if not hasattr(handler, '_attrs_static_'):
                    handler._attrs_static_ = defaultdict(list)
                handler._attrs_static_[trigger].append(self)

            if handler in self.handlers[trigger]:
                raise AttributeError(f'This @on(\'{trigger}\') handler is already set')
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

        return getattr(instance.mount_element, self.name, None)

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

    def __mount_tag__(self, ctx: Context):
        if self.provider is None:
            self.provider = ctx
        else:
            self.subscribers.append(ctx)

    def __set__(self, instance, value, _prevent_model=False):
        super().__set__(instance, value, _prevent_model=_prevent_model)
        if instance is self.provider:
            for ctx in self.subscribers:
                ctx.__notify__(self.name, self, value)


__all__ = ['attr', 'state', 'html_attr']
