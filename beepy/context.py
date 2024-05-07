from __future__ import annotations

import enum
from abc import ABCMeta
from typing import TYPE_CHECKING, Self

import beepy
from beepy.attrs import attr, html_attr, state, state_move_on
from beepy.utils import IN_BROWSER, __config__, js
from beepy.utils.common import get_random_name, log10_ceil, to_kebab_case
from beepy.utils.js_py import Interval, create_once_callable

if TYPE_CHECKING:
    from beepy.types import AttrType

_base_obj_dir = (*dir(object()), '__abstractmethods__')
_context_initialized = False


class SpecialChild(enum.StrEnum):
    OVERWRITE = 'OVERWRITE'
    SUPER = 'SUPER'
    CONTENT = 'CONTENT'


class _MetaContext(ABCMeta):
    _to_load_before_top_render: list = []
    _wait_onload_interval: dict[Context, Interval] = {}
    _context_classes = []
    __clean_class_attribute_names = ()
    _current_render = {None: []}  # to prevent ValueError, for now
    _contexts: list[Context]

    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):
        initialized = _context_initialized  # if class Context is already defined

        # used for checking inheritance: attributes, methods, etc.
        # for example: extending classes Tag and WithRouter must produce correct state 'router'
        # TODO: move this (or part of this) to _MetaContext.__init__
        base_cls: type[Context] | type = type.__new__(mcs, _name, bases, {})

        namespace = namespace.copy()
        namespace.setdefault('__slots__', ())
        static_attrs = {}
        attrs_defaults = {}

        if initialized and hasattr(beepy, 'children'):
            _children = beepy.children

            mcs._update_namespace_with_extra_attributes(namespace)

            for attribute_name, child in mcs._clean_namespace(namespace):
                if isinstance(child, state):
                    static_attrs[attribute_name] = child

            for attribute_name, child in mcs._clean_cls_iter(base_cls):
                new_attr = namespace.get(attribute_name)
                if attribute_name not in static_attrs and isinstance(child, state):
                    static_attrs[attribute_name] = child

                if new_attr and (
                    (isinstance(child, state) and not isinstance(new_attr, state))
                    or (isinstance(child, _children.ChildrenRef) and not isinstance(new_attr, _children.ChildrenRef))
                ):
                    attrs_defaults[attribute_name] = namespace.pop(attribute_name)

        is_root = kwargs.get('_root')
        ctx_name = '' if is_root else kwargs.get('name')
        namespace['_meta_root'] = is_root

        if ctx_name or (initialized and not hasattr(base_cls, '_context_name_')):
            namespace['_context_name_'] = ctx_name or to_kebab_case(_name)

        cls: type[Context] | type = super().__new__(mcs, _name, bases, namespace)

        if initialized:
            cls._static_attrs = state._order_dict_by_priority(cls._static_attrs.copy() | static_attrs)
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
    def _top_mount(mcs, element):
        parent = element._root_parent
        root = parent.mount_element
        using_ssr = __config__['server_side'] == 'client'
        if not using_ssr:
            root.style = 'visibility: hidden'

        mcs._current_render[parent] = []

        if using_ssr:
            element.__mount__(js.beepy.addElement(root, 'template'), parent)
            element.mount_parent = root
        else:
            element.__mount__(root, parent)

        mcs._wait_onload_interval[parent] = Interval(mcs._wait_onload, (element,), period=0.2)

        if not IN_BROWSER:
            mcs._ssr2__finish()

    @classmethod
    def _ssr2__finish(mcs):
        # SSR implementation without selenium
        # I want to try using bs4 instead of js.py mock
        # Not really working right now
        import time

        mcs._to_load_before_top_render.clear()

        time.sleep(1)

        for thread in js.threads_to_join:
            thread.join()
        js.threads_to_join.clear()
        for thread in (*js.threads['timeout'].values(), *js.threads['interval'].values()):
            thread.join()

        print(js.document.documentElement.outerHTML)

    @classmethod
    def _top_render(mcs, element):
        root = element._root_parent.mount_element
        using_ssr = __config__['server_side'] == 'client'

        if not using_ssr:
            root.style = ''
            js.beepy.stopLoading()

        element.__render__()

        if using_ssr:
            template = element.mount_element.parentElement
            root.replaceChild(element.mount_element, root.children[0])
            template.remove()

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
            mcs._to_load_before_top_render.remove(onload)

        mcs._to_load_before_top_render.append(onload)
        return onload

    @classmethod
    def _wait_onload(mcs, element):
        if not mcs._to_load_before_top_render:
            if interval := mcs._wait_onload_interval.get(element._root_parent):
                interval.clear()
                mcs._wait_onload_interval.pop(element._root_parent)
            mcs._top_render(element)


class Context(metaclass=_MetaContext, _root=True):
    __slots__ = ('_id_', '_args', '_kwargs', 'attrs')

    _meta_root = False

    _id_: str
    _args: tuple[AttrType, ...]
    _kwargs: dict[str, AttrType]

    _static_attrs: dict[str, state]
    _attrs_defaults: dict[str, AttrType]
    attrs: dict[str, state]
    _context_name_: str

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.attrs = self._static_attrs.copy()

        # define some attributes here, not in __init__, because they are used for __hash__ method
        self._id_ = get_random_name(log10_ceil(len(self._contexts) * len(self.__class__._context_classes)))
        self._args = args
        self._kwargs = kwargs

        if not _context_initialized:
            return self

        for name, attribute in self.attrs.items():
            attribute._link_cmpt(name, self, force=False)

        return self

    def _clone_link_parent(self, parent):
        for name, attribute in self.attrs.items():
            if name in self._kwargs:
                attribute._set_first_value(self, self._kwargs[name], parent)
        self._link_parent_attrs(parent)

    def _link_parent_attrs(self, parent):
        p_data = parent._attrs_defaults | parent._kwargs

        for name, attr_to_move_on in parent.attrs.items():
            if isinstance(attr_to_move_on, state_move_on):
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
            attr_._init_ctx(self, value)

        self.post_init()

    def post_init(self):
        pass

    @property
    def _attrs_values(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr._get_view_value(self)
            for _attr in self.attrs.values()
            if isinstance(_attr, attr) and not isinstance(_attr, html_attr)
        }

    @property
    def _states(self) -> dict[str, AttrType]:
        return {_attr.name: _attr.__get__(self) for _attr in self.attrs.values()}

    @property
    def _args_kwargs(self):
        if not hasattr(self, '_args'):
            return None
        # TODO: make self._kwargs as frozendict
        return self._args, self._kwargs

    def __hash__(self):
        # TODO: make force immutable this attributes
        return hash((self._context_name_, self._id_))

    def __notify__(self, attr_name: str, attribute: state, value: AttrType):
        pass

    def _clone(self, parent=None) -> Self:
        clone = type(self)(*self._args, **self._kwargs)
        clone._clone_link_parent(parent)
        return clone


_context_initialized = True


__all__ = ['SpecialChild', '_MetaContext', 'Context']
