from __future__ import annotations as _

from typing import Optional, Callable, Union, Iterable, Type, get_type_hints, ForwardRef, TypeVar
from collections import defaultdict

from .types import AttrType, AttrValue
from .utils import log, NONE_TYPE, to_kebab_case


Context = ForwardRef('Context')
T = TypeVar('T')


class attr:
    __slots__ = (
        'name', 'initial_value', 'type',
        'const', 'required', 'notify',
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
    fget: Callable[[Context], T]
    fset: Callable[[Context, T], None]
    fdel: Callable[[Context], None]
    handlers: dict[str, list[Callable[[Context, T], None], ...]]
    enum: Iterable

    _cache: dict[Context, AttrType]

    def __init__(
        self, initial_value=None, /, *,
        const=False, required=False, notify=False,
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

        if initial_value is None and _type is None:
            self.type = NONE_TYPE
        else:
            if _type is None:
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

    def __set__(self, instance, value):
        if self.const and self.__get__(instance) is not None:
            raise AttributeError

        log.debug('[__SET__]', instance, self.name, value)
        (self.fset or self._fset)(instance, value)

        for trigger in self.handlers['change']:
            trigger(instance, value)

        if self.notify:
            instance.__notify__(self.name, self, value)

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

    def _link_ctx(self, name: str, ctx: Context, force: bool = True):
        ctx.attrs[name] = self
        if force:
            self.__set_name__(ctx, name)
        if not hasattr(ctx, name) and hasattr(ctx, 'mount_element'):
            setattr(ctx, name, self.__get__(ctx))
        return self

    def __mount_tag__(self, ctx: Context):
        pass

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
        return f'{self.name}(default={self.initial_value!r})'

    def on(self, trigger):
        def wrapper(handler):
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


class static_state(state):
    __slots__ = ()

    _static = True  # unused for now

    def on(self, trigger):
        _super = super()

        def wrapper(handler):
            if not hasattr(handler, '_attrs_static_'):
                handler._attrs_static_ = defaultdict(list)
            handler._attrs_static_[trigger].append(self)
            return _super.on(trigger)(handler)

        return wrapper


class html_attr(attr):
    __slots__ = ()

    _view = False

    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        # TODO: is it possible to create listener on change value?
        return getattr(instance.mount_element, self.name, None)

    def __set__(self, instance, value):
        if hasattr(instance, 'mount_element'):
            value = self._get_view_value(value=value)
            # attributes are set like setAttribute, if attribute is native, even if it's hidden
            setattr(instance.mount_element, self.name, value)

    def __del__(self, instance):
        delattr(instance.mount_element, self.name)


__all__ = ['attr', 'state', 'html_attr']
