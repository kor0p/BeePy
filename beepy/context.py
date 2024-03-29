from __future__ import annotations

from abc import ABCMeta
from typing import TYPE_CHECKING, TypeVar

from boltons.typeutils import make_sentinel

import beepy
from beepy.attrs import attr
from beepy.utils import js
from beepy.utils.common import get_random_name, log10_ceil, to_kebab_case
from beepy.utils.js_py import Interval, create_once_callable

if TYPE_CHECKING:
    from beepy.types import AttrType

_base_obj_dir = (*dir(object()), '__abstractmethods__')


Self = TypeVar('Self', bound='Context')

_CONTEXT_INITIALIZED = False

OVERWRITE = make_sentinel('_OVERWRITE', var_name='OVERWRITE')
SUPER = make_sentinel('_SUPER', var_name='SUPER')
CONTENT = make_sentinel('_CONTENT', var_name='CONTENT')
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
        base_cls: type[Context] | type = type.__new__(mcs, _name, bases, {})

        namespace = namespace.copy()
        namespace.setdefault('__slots__', ())
        static_attrs = {}
        attrs_defaults = {}

        if initialized and hasattr(beepy, 'children'):
            _children = beepy.children

            mcs._update_namespace_with_extra_attributes(namespace)

            for attribute_name, child in mcs._clean_namespace(namespace):
                if isinstance(child, attr):
                    static_attrs[attribute_name] = child

            for attribute_name, child in mcs._clean_cls_iter(base_cls):
                new_attr = namespace.get(attribute_name)
                if attribute_name not in static_attrs and isinstance(child, attr):
                    static_attrs[attribute_name] = child

                if new_attr and (
                    (isinstance(child, attr) and not isinstance(new_attr, attr))
                    or (isinstance(child, _children.ChildrenRef) and not isinstance(new_attr, _children.ChildrenRef))
                ):
                    attrs_defaults[attribute_name] = namespace.pop(attribute_name)

        is_root = kwargs.get('_root')
        ctx_name = '' if is_root else kwargs.get('name')
        namespace['__ROOT__'] = is_root

        if ctx_name or (initialized and not hasattr(base_cls, '_context_name_')):
            namespace['_context_name_'] = ctx_name or to_kebab_case(_name)

        cls: type[Context] | type = super().__new__(mcs, _name, bases, namespace)

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
    def _update_namespace_with_extra_attributes(mcs, namespace):
        if not hasattr(beepy, 'children'):
            return

        for _attribute_name, child in mcs._clean_namespace(namespace):
            if isinstance(child, beepy.children.ChildRef | Context) and (
                extra := getattr((child if isinstance(child, Context) else child.child), '__extra_attributes__', None)
            ):
                extra = {key: value for key, value in extra.items() if key not in namespace}
                namespace.update(extra)

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
        element._root_parent.mount_element.style = ''
        js.beepy.stopLoading()
        element.__render__()

    @classmethod
    def _clean_namespace(mcs, namespace):
        base_obj_dir = _base_obj_dir + mcs.__clean_class_attribute_names
        for key, value in tuple(namespace.items()):
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
                mcs._wait_onload_interval.pop(element._root_parent)
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
            attribute._link_cmpt(name, self, force=False)
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
                attr_to_move_on._link_cmpt(name, self, force_cls_set=True)
                if name in p_data:
                    self._attrs_defaults[name] = p_data[name]

    def __init__(self, *args, **kwargs: AttrType):
        self.__class__._contexts.append(self)
        data = self._attrs_defaults | kwargs
        self.init(*args, **data)

    def init(self, *_args, **kwargs):
        for key, attr_ in self.attrs.items():
            if key not in kwargs:
                if attr_.required:
                    raise TypeError(f'Attribute {attr_.name!r} is required')
                continue

            value = kwargs[key]
            setattr(self, key, value)
            attr_.__init_ctx__(self, value)

        self.post_init()

    def post_init(self):
        pass

    @property
    def __view_attrs__(self) -> dict[str, AttrType]:
        return {_attr.name: _attr._get_view_value(self) for _attr in self.attrs.values() if _attr._view}

    @property
    def __attrs__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr._get_view_value(self)
            for _attr in self.attrs.values()
            if _attr._view and not _attr._set_on_render
        }

    @property
    def __states__(self) -> dict[str, AttrType]:
        return {_attr.name: _attr.__get__(self) for _attr in self.attrs.values()}

    @property
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


__all__ = ['OVERWRITE', 'SUPER', 'CONTENT', '_SPECIAL_CHILD_STRINGS', '_MetaContext', 'Context']
