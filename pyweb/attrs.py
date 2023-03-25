from __future__ import annotations as _

from functools import partial
from typing import Optional, Callable, Union, Iterable, Type, get_type_hints, ForwardRef, TypeVar, Any
from collections import defaultdict

from .types import AttrType, AttrValue
from .utils import log, NONE_TYPE, wraps_with_name, to_kebab_case, add_event_listener, set_timeout


Context = ForwardRef('Context')
T = TypeVar('T')


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
    handlers: dict[str, list[Callable[[Context, T], None], ...]]
    enum: Iterable

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

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return (self.fget or self._fget)(instance)

    def _fget(self, instance):
        return self._cache.get(instance, self.initial_value)

    def __call__(self, fget):
        self.fget = fget
        self.name = to_kebab_case(fget.__name__)
        if self.type is NONE_TYPE:
            annotations = get_type_hints(fget)
            if 'return' in annotations:
                self._set_type(annotations['return'])
        return self

    def __set__(self, instance, value, _prevent_model=False):
        if self.const and self.__get__(instance) is not None:
            raise AttributeError

        log.debug('[__SET__]', instance, self.name, value)
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

        self._cache[instance] = value

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

        # print(f'[+---+] {owner} {self._from_model_cache} {name} {self}')
        # for index, (instance, _attr, _) in enumerate(self._from_model_cache):
        #     print(f'[---] {owner} {instance} {_attr} {name} {self}')
        #     if isinstance(instance, owner):
        #         self._from_model_cache[index] = (instance, _attr, name)

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

    def _prepare_attribute_for_model(self, instance, value):
        if attribute := self.model_options['attribute']:
            if callable(attribute):
                return attribute(instance, value)
            return attribute

    def _handle_model_listeners(self, ctx: Context):
        to_remove_indexes = []

        for index, (instance, attr_, name) in enumerate(self._from_model_cache):
            log.warn(f'[HERE] {ctx} {instance} {attr_} {name}')
            if name is None:
                to_remove_indexes.append(index)
                continue

            if instance.parent_defined:
                value = self.__get__(instance.parent)
            else:
                value = self.__get__(False)
            if value is None:
                if self.initial_value is not None:
                    value = self.initial_value
                elif self.type:
                    __value = self._get_type_instance(error_text=f'Will be better to set {self.name} not to None')
                    if __value is not None:
                        value = __value
            if attribute_ := self._prepare_attribute_for_model(instance, value):
                value = getattr(value, attribute_)
            if value is None:
                value = ''

            attr_.__set__(instance, value, _prevent_model=True)

            _attribute_str = f'({attribute_})' if attribute_ else ''

            @instance.on(attr_.model)
            @wraps_with_name(f'@attr[to:{attr_}->model{_attribute_str}->{self}]')
            def __handler_to_model(parent_instance, _event, current_instance=instance):
                _value = _event.target.value
                if attribute := self._prepare_attribute_for_model(current_instance, _value):
                    setattr(self.__get__(parent_instance), attribute, _value)
                else:
                    self.__set__(parent_instance, _value, _prevent_model=True)

            @self.on('change')
            @wraps_with_name(f'@attr[from:{attr_}->model{_attribute_str}->{self}]')
            def __handler_from_model(parent_instance, _value, current_instance=instance, current_attribute=attribute_):
                if current_attribute is None:
                    instance_ = current_instance
                else:
                    instance_ = getattr(parent_instance, current_attribute)

                if attribute := self._prepare_attribute_for_model(current_instance, _value):
                    _value = getattr(_value, attribute)

                attr_.__set__(instance_, _value, _prevent_model=True)

        for index in reversed(to_remove_indexes):
            self._from_model_cache.pop(index)

    def __mount_tag__(self, ctx: Context):
        self._handle_model_listeners(ctx)

    def __delete__(self, instance):
        return (self.fdel or self._fdel)(instance)

    def _fdel(self, instance):
        if self.fget is not None:
            raise AttributeError

        del self._cache[instance]

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

        if issubclass(self.type, bool):
            if value:
                return ''
            else:
                return

        # support for custom types for attr
        if isinstance(self.type, AttrValue):
            return value.__view_value__()

        return value


class state(attr):
    __slots__ = ()

    _view = False


class html_attr(attr):
    __slots__ = ()

    _view = False

    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        if self.name is None:
            self.name = name

    def _fget(self, instance):
        if instance is None:
            return self

        return getattr(instance.mount_element, self.name, None)

    def _fset(self, instance, value):
        if hasattr(instance, 'mount_element'):
            value = self._get_view_value(value=value)
            # attributes are set like setAttribute, if attribute is native, even if it's hidden
            setattr(instance.mount_element, self.name, value)

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
