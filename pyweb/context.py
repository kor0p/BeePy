from __future__ import annotations

from abc import ABCMeta
from typing import Union, Type, TypeVar

import pyweb

from .attrs import attr
from .types import AttrType
from .utils import log, log10_ceil, get_random_name, const_attribute


Self = TypeVar('Self', bound='Context')

_CONTEXT_INITIALIZED = False


class _MetaContext(ABCMeta):
    _context_classes = []
    __clean_class_attribute_names = ()
    _contexts: list[Context, ...]

    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):
        initialized = _CONTEXT_INITIALIZED  # if class Context is already defined

        namespace = namespace.copy()
        namespace.setdefault('__slots__', ())
        static_attrs = {}

        if initialized and hasattr(pyweb, 'children'):
            extra_attrs = []
            for attribute_name, child in mcs._clean_namespace(namespace):
                if isinstance(child, pyweb.children.ChildRef) and (
                    cls_extra_attrs := getattr(child.child, '__extra_attrs__', None)
                ):
                    extra_attrs.extend(cls_extra_attrs)
                if isinstance(child, attr):
                    static_attrs[attribute_name] = child

            namespace['__slots__'] = (*extra_attrs, *namespace['__slots__'])

        log.debug('[__NAMESPACE__]', namespace)

        is_root = kwargs.get('_root')
        if is_root:
            ctx_name = ''
        else:
            ctx_name = kwargs.get('name')
        namespace['__ROOT__'] = is_root

        if ctx_name:
            namespace['_context_name_'] = ctx_name

        cls: Union[Type[Context], type] = super().__new__(mcs, _name, bases, namespace)

        if initialized:
            cls.static_attrs = cls.static_attrs.copy() | static_attrs
        else:
            cls.static_attrs = {}

        cls._contexts = []

        mcs._context_classes.append(cls)

        return cls

    @classmethod
    def _resolve_annotations(mcs):
        # TODO: fix too many calls of get_type_hints
        # for cls in mcs._context_classes:
        #     for name, _type in get_type_hints(cls).items():
        #         if not (attribute := getattr(cls, name, None)) or not isinstance(attribute, attr):
        #             continue
        #
        #         attribute._set_type(_type)
        """ not working, use attr(type=str) notation """

    @classmethod
    def _pre_top_mount(mcs):
        mcs._resolve_annotations()

    @classmethod
    def _clean_namespace(mcs, namespace):
        for key, value in namespace.items():
            if key not in mcs.__clean_class_attribute_names:
                yield key, value


class Context(metaclass=_MetaContext, _root=True):
    __slots__ = ('_id_', '_args', '_kwargs', 'attrs')

    __ROOT__ = False

    _id_: str
    _args: tuple[AttrType, ...]
    _kwargs: dict[str, AttrType]

    static_attrs: dict[str, attr]
    attrs: dict[str, attr]
    _context_name_: str

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.attrs = self.static_attrs.copy()

        # define some attributes here, not in __init__, because they are used for __hash__ method
        self._id_ = get_random_name(log10_ceil(len(self._contexts) * len(self.__class__._context_classes)))
        self.args_kwargs = args, kwargs

        if _CONTEXT_INITIALIZED:
            for name, attribute in self.static_attrs.items():
                if hasattr(attribute, '_link_ctx'):
                    attribute._link_ctx(name, self, force=False)

        return self

    def __init__(self, *args, **kwargs: AttrType):
        self.__class__._contexts.append(self)
        for key, _attr in self.attrs.items():
            if key not in kwargs:
                if _attr.required:
                    raise TypeError(f'Attribute {_attr.name!r} is required')
                continue

            value = kwargs[key]

            setattr(self, key, value)

    @property
    def __attrs__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr._get_view_value(self)
            for _attr in self.attrs.values()
            if _attr._view
        }

    @property
    def __states__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr.__get__(self)
            for _attr in self.attrs.values()
        }

    @const_attribute
    def args_kwargs(self):
        if not hasattr(self, '_args'):
            return None
        return self._args, self._kwargs

    @args_kwargs.setter
    def args_kwargs(self, value):
        self._args, self._kwargs = value

    def __hash__(self):
        # TODO: make force immutable this attributes
        return hash((self._context_name_, self._id_))

    def __notify__(self, attr_name: str, attribute: attr, value: AttrType):
        pass

    def clone(self) -> Self:
        args, kwargs = self.args_kwargs
        return type(self)(*args, **kwargs)


_CONTEXT_INITIALIZED = True


__all__ = ['_MetaContext', 'Context']
