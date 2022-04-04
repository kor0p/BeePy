from __future__ import annotations as _

from typing import Optional, Any, Callable, Union, Type, get_type_hints, ForwardRef

from .types import AttrType, AttrValue
from .utils import log, NONE_TYPE, to_kebab_case


Context = ForwardRef('Context')


class attr:
    __slots__ = (
        'name', 'const', 'value', 'required', 'type', 'fget', 'fset', 'fdel', 'onchange_trigger', 'enum', '_cache',
    )

    _view = True

    name: Optional[str]
    value: Any
    type: Optional[Union[type, Type[Context]]]
    fget: Callable
    fset: Callable
    fdel: Callable

    _cache: dict[Context, AttrType]

    def __init__(
        self, value=None, *,
        const=False, required=False,
        fget=None, fset=None, fdel=None,
        onchange_trigger=None,
        enum=None,
    ):
        self.name = None
        self.const = const
        assert not const or value is None, f'Const {type(self).__name__} cannot have initial value'
        self.value = value
        self.required = required or const  # const attr must be also required
        self.type = NONE_TYPE

        # TODO: think on: is this needed?
        # behaviour like @property
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if fget:
            self(fget)

        self.onchange_trigger = onchange_trigger
        self.enum = enum

        self._cache = {}

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return (self.fget or self._fget)(instance)

    def _fget(self, instance):
        return self._cache.get(instance, self.value)

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
        if self.onchange_trigger:
            self.onchange_trigger(instance, value)

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

    def _set_type(self, _type):
        if hasattr(_type, '__origin__'):
            _type = _type.__origin__
        try:
            issubclass(_type, type)
        except TypeError:
            log.error(f'Bad type for attribute: {_type!r}, {type(_type)}')
            return
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
        return f'{self.name}(default={self.value!r})'

    def onchange(self, handler):
        self.onchange_trigger = handler
        return handler

    def _get_view_value(self, instance):
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
        if self.name is None:
            self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return getattr(instance.mount_element, self.name, None)

    def __set__(self, instance, value):
        if hasattr(instance, 'mount_element'):
            # attributes is set like setAttribute, if attribute is native, even if it's hidden
            setattr(instance.mount_element, self.name, value)

    def __del__(self, instance):
        delattr(instance.mount_element, self.name)


__all__ = ['attr', 'state', 'html_attr']
