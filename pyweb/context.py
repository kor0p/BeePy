from __future__ import annotations

from abc import ABCMeta
from typing import Union, Type, TypeVar

import pyweb

from .attrs import attr
from .types import AttrType
from .utils import log, log10_ceil, get_random_name, const_attribute


__obj = object()
_base_obj_dir = tuple(dir(__obj)) + ('__abstractmethods__',)


Self = TypeVar('Self', bound='Context')

_CONTEXT_INITIALIZED = False

OVERWRITE = '__OVERWRITE__'
SUPER = '__SUPER__'
CONTENT = '__CONTENT__'
_SPECIAL_CHILD_STRINGS = (OVERWRITE, SUPER, CONTENT)


class _MetaContext(ABCMeta):
    _context_classes = []
    __clean_class_attribute_names = ()
    _contexts: list[Context, ...]

    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):
        initialized = _CONTEXT_INITIALIZED  # if class Context is already defined

        # used for checking inheritance: attributes, methods, etc.
        # for example: extending classes Tag and WithRouter must produce correct state 'router'
        base_cls: Union[Type[Context], type] = type.__new__(mcs, _name, bases, {})

        namespace = namespace.copy()
        namespace.setdefault('__slots__', ())
        static_attrs = {}
        attrs_defaults = {}

        if initialized and hasattr(pyweb, 'children'):
            _children = pyweb.children

            extra_attrs = []
            for attribute_name, child in mcs._clean_namespace(namespace):
                if isinstance(child, _children.ChildRef) and (
                    cls_extra_attrs := getattr(child.child, '__extra_attrs__', None)
                ):
                    extra_attrs.extend(cls_extra_attrs)

                if isinstance(child, attr):
                    static_attrs[attribute_name] = child

            for attribute_name, child in mcs._clean_cls_iter(base_cls):
                new_attr = namespace.get(attribute_name)
                if attribute_name not in static_attrs and isinstance(child, attr):
                    static_attrs[attribute_name] = child

                if new_attr and (
                    (isinstance(child, attr) and not isinstance(new_attr, attr)) or
                    (isinstance(child, _children.ChildrenRef) and not isinstance(new_attr, _children.ChildrenRef))
                ):
                    attrs_defaults[attribute_name] = namespace.pop(attribute_name)

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
            cls._static_attrs = cls._static_attrs.copy() | static_attrs
            cls._attrs_defaults = cls._attrs_defaults.copy() | attrs_defaults
        else:
            cls._static_attrs = {}
            cls._attrs_defaults = {}

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
        base_obj_dir = _base_obj_dir + mcs.__clean_class_attribute_names
        for key, value in namespace.items():
            if key not in base_obj_dir:
                yield key, value

    @classmethod
    def _clean_cls_iter(mcs, cls):
        base_obj_dir = _base_obj_dir + mcs.__clean_class_attribute_names
        for key in dir(cls):
            if key not in base_obj_dir:
                yield key, getattr(cls, key)


class Context(metaclass=_MetaContext, _root=True):
    __slots__ = ('_id_', '_args', '_kwargs', 'attrs')

    __ROOT__ = False

    _id_: str
    _args: tuple[AttrType, ...]
    _kwargs: dict[str, AttrType]

    _static_attrs: dict[str, attr]
    _attrs_defaults: dict[str, AttrType]
    attrs: dict[str, attr]
    _context_name_: str

    def __new__(cls, *args, **kwargs):
        parent = kwargs.pop('__parent__', None)
        self = super().__new__(cls)
        self.attrs = self._static_attrs.copy()

        # define some attributes here, not in __init__, because they are used for __hash__ method
        self._id_ = get_random_name(log10_ceil(len(self._contexts) * len(self.__class__._context_classes)))
        self._args = args
        self._kwargs = kwargs

        if not _CONTEXT_INITIALIZED:
            return self

        for name, attribute in self.attrs.items():
            attribute._link_ctx(name, self, force=False)
            if parent and name in kwargs:
                attribute.__set_first__(self, kwargs[name], parent)

        if parent:
            p_args, p_kwargs = parent.args_kwargs
            p_data = parent._attrs_defaults | p_kwargs

            for name, attr_to_move_on in parent.attrs.items():
                if attr_to_move_on.move_on:
                    attr_to_move_on._link_ctx(name, self, force_cls_set=True)
                    if name in p_data:
                        self._attrs_defaults[name] = p_data[name]

        return self

    def __init__(self, *args, **kwargs: AttrType):
        self.__class__._contexts.append(self)
        data = self._attrs_defaults | kwargs
        self.init(*args, **data)

    def init(self, *args, **kwargs):
        for key, _attr in self.attrs.items():
            if key not in kwargs:
                if _attr.required:
                    raise TypeError(f'Attribute {_attr.name!r} is required')
                continue

            setattr(self, key, kwargs[key])

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
        # TODO: make self._kwargs as frozendict
        return self._args, self._kwargs

    def __hash__(self):
        # TODO: make force immutable this attributes
        return hash((self._context_name_, self._id_))

    def __notify__(self, attr_name: str, attribute: attr, value: AttrType):
        pass

    def clone(self, parent=None) -> Self:
        args, kwargs = self.args_kwargs
        if parent is not None:
            kwargs = kwargs | {'__parent__': parent}
        return type(self)(*args, **kwargs)


_CONTEXT_INITIALIZED = True


__all__ = ['SUPER', 'CONTENT', '_SPECIAL_CHILD_STRINGS', '_MetaContext', 'Context']
