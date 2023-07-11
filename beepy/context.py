from __future__ import annotations

from abc import ABCMeta
from typing import Union, Type, TypeVar

import beepy

from beepy.attrs import attr
from beepy.types import AttrType
from beepy.utils import js
from beepy.utils.dev import const_attribute
from beepy.utils.common import log10_ceil, get_random_name, to_kebab_case
from beepy.utils.js_py import create_once_callable, Interval


__obj = object()
_base_obj_dir = tuple(dir(__obj)) + ('__abstractmethods__',)


Self = TypeVar('Self', bound='Context')

_CONTEXT_INITIALIZED = False

OVERWRITE = '__OVERWRITE__'
SUPER = '__SUPER__'
CONTENT = '__CONTENT__'
_SPECIAL_CHILD_STRINGS = (OVERWRITE, SUPER, CONTENT)


class _MetaContext(ABCMeta):
    _to_load_before_top_render: dict[Context | None, list] = {None: []}
    _wait_onload_interval: dict[Context, Interval] = {}
    _context_classes = []
    __clean_class_attribute_names = ()
    _current_render = {None: []}  # to prevent ValueError, for now
    _contexts: list[Context]

    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):
        initialized = _CONTEXT_INITIALIZED  # if class Context is already defined

        # used for checking inheritance: attributes, methods, etc.
        # for example: extending classes Tag and WithRouter must produce correct state 'router'
        base_cls: Union[Type[Context], type] = type.__new__(mcs, _name, bases, {})

        namespace = namespace.copy()
        namespace.setdefault('__slots__', ())
        static_attrs = {}
        attrs_defaults = {}

        if initialized and hasattr(beepy, 'children'):
            _children = beepy.children

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

        is_root = kwargs.get('_root')
        if is_root:
            ctx_name = ''
        else:
            ctx_name = kwargs.get('name')
        namespace['__ROOT__'] = is_root

        if ctx_name or (initialized and not hasattr(base_cls, '_context_name_')):
            namespace['_context_name_'] = ctx_name or to_kebab_case(_name)

        cls: Union[Type[Context], type] = super().__new__(mcs, _name, bases, namespace)

        if initialized:
            cls._static_attrs = attr.order_dict_by_priority(cls._static_attrs.copy() | static_attrs)
            cls._attrs_defaults = cls._attrs_defaults.copy() | attrs_defaults
        else:
            cls._static_attrs = {}
            cls._attrs_defaults = {}

        cls._contexts = []

        mcs._context_classes.append(cls)

        return cls

    @classmethod
    def _top_mount(mcs, element, root, parent):
        root.style = 'visibility: hidden'
        mcs._current_render[parent] = []
        element.__mount__(root, parent)

    @classmethod
    def _top_render(mcs, element):
        mcs._wait_onload_interval[element._root_parent] = Interval(mcs.wait_onload, (element,), period=0.2)

    @classmethod
    def _top_render_real(mcs, element):
        element.__render__()
        element._root_parent.mount_element.style = ''
        js.beepy.stopLoading()

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

    @classmethod
    def create_onload(mcs):
        @create_once_callable
        def onload(*_, **__):
            mcs._to_load_before_top_render[None].remove(onload)

        mcs._to_load_before_top_render[None].append(onload)
        return onload

    @classmethod
    def wait_onload(mcs, element):
        if not mcs._to_load_before_top_render[None] and not mcs._to_load_before_top_render.get(element._root_parent):
            if interval := mcs._wait_onload_interval.get(element._root_parent):
                interval.clear()
            mcs._top_render_real(element)


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
            self.link_parent_attrs(parent)

        return self

    def link_parent_attrs(self, parent):
        p_args, p_kwargs = parent.args_kwargs
        p_data = parent._attrs_defaults | p_kwargs

        for name, attr_to_move_on in parent.attrs.items():
            if attr_to_move_on.move_on:
                attr_to_move_on._link_ctx(name, self, force_cls_set=True)
                if name in p_data:
                    self._attrs_defaults[name] = p_data[name]

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
    def __view_attrs__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr._get_view_value(self)
            for _attr in self.attrs.values()
            if _attr._view
        }

    @property
    def __attrs__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr._get_view_value(self)
            for _attr in self.attrs.values()
            if _attr._view and not _attr._set_on_render
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
