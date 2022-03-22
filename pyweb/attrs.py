from __future__ import annotations as _

from typing import Optional, Any, Callable, Union, Type, get_type_hints

from .types import Tag, AttrValue
from .utils import log, NONE_TYPE, to_kebab_case


class attr:
    _view = True

    __slots__ = (
        'name', 'private_name', 'const', 'value', 'required', 'type', 'fget', 'fset', 'fdel', 'onchange_trigger',
        'enum',
    )

    name: Optional[str]
    private_name: Optional[str]
    value: Any
    type: Optional[Union[type, Type[Tag]]]
    fget: Callable
    fset: Callable
    fdel: Callable

    def __init__(
        self, value=None, *,
        const=False, required=False,
        fget=None, fset=None, fdel=None,
        onchange_trigger=None,
        enum=None,
    ):
        self.name = None
        self.private_name = None
        self.const = const
        assert not const or value is None, f'Const {type(self).__name__} cannot have initial value'
        self.value = value
        self.required = required or const  # const attr must be also required

        self.fget = fget or self._fget
        self.fset = fset or self._fset
        self.fdel = fdel or self._fdel

        self.type = NONE_TYPE
        if fget:
            self(fget)

        self.onchange_trigger = onchange_trigger
        self.enum = enum

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self.fget(instance)

    def _fget(self, instance):
        return getattr(instance, self.private_name, None)

    def __call__(self, fget):
        self.fget = fget
        self.name = to_kebab_case(fget.__name__)
        if self.type is NONE_TYPE:
            annotations = get_type_hints(fget)
            if 'return' in annotations:
                self.__set_type__(annotations['return'])
        return self

    def __set__(self, instance, value):
        if self.const and getattr(instance, self.private_name, None) is not None:
            raise AttributeError
        log.debug('[__SET__]', instance, self.name, value)
        self.fset(instance, value)
        if self.onchange_trigger:
            self.onchange_trigger(instance, value)

    def _fset(self, instance, value):
        if not self.fget:
            raise AttributeError
        if self.enum is not None and value not in self.enum:
            raise TypeError(f'Possible values: {self.enum}. Provided value: {value}')
        setattr(instance, self.private_name, value)

    def setter(self, fset):
        self.fset = fset
        if self.type is NONE_TYPE:
            self.__set_type__(tuple(get_type_hints(fset).values())[0])
        return self

    def __set_name__(self, owner, name):
        if self._view:
            view_name = to_kebab_case(name)
        else:
            view_name = name
        self.name = view_name
        self.private_name = '__attr_' + name
        if self.value is not None:
            self.__set__(owner, self.value)

    def __set_type__(self, _type):
        if hasattr(_type, '__origin__'):
            _type = _type.__origin__
        try:
            issubclass(_type, type)
        except TypeError:
            log.error(f'Bad type for attribute: {_type!r}, {type(_type)}')
            return
        self.type = _type

    def __set_to_tag__(self, name: str, tag: Optional[Union[Tag, Type[Tag]]], force: bool = False):
        tag.attrs[name] = self
        if force:
            self.__set_name__(tag, name)
        if not hasattr(tag, name):
            setattr(tag, name, self.__get__(tag))

    def __delete__(self, instance):
        return self.fdel(instance)

    def _fdel(self, instance):
        if not self.fget:
            raise AttributeError
        return delattr(instance, self.private_name)

    def deleter(self, fdel):
        self.fdel = fdel
        return self

    def __repr__(self):
        return f'{self.name}(default={self.value!r})'

    def onchange(self, handler):
        self.onchange_trigger = handler
        return handler

    def __get_view_value__(self, instance):
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
