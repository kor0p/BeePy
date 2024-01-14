from __future__ import annotations

import traceback
from collections.abc import Callable, Iterable
from functools import cache
from types import MethodType

from beepy.attrs import attr, set_html_attribute, state
from beepy.children import ChildRef, Children, ContentWrapper, CustomWrapper, StringWrapper, TagRef
from beepy.components import Component, _MetaComponent
from beepy.context import _SPECIAL_CHILD_STRINGS, CONTENT, OVERWRITE, SUPER
from beepy.types import AttrType, ContentType, Mounter, Renderer
from beepy.utils import __CONFIG__, js, log
from beepy.utils.common import NONE_TYPE, get_random_name, to_kebab_case
from beepy.utils.dev import _debugger
from beepy.utils.internal import _PY_TAG_ATTRIBUTE

__version__ = '0.8.5'  # For internal development set to 0.0a0
__CONFIG__['version'] = __version__


_TAG_INITIALIZED = False


class _MetaTag(_MetaComponent):
    _tag_classes: list[type[Tag]] = []
    __clean_class_attribute_names = ('_content_tag', '_static_children_tag')

    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):  # noqa: PLR0912, PLR0915
        namespace = namespace.copy()
        namespace.setdefault('__slots__', ())
        if '_content' in namespace:
            namespace['_static_content'] = namespace.pop('_content')

        # used for checking inheritance: attributes, methods, etc.
        # for example: extending classes Tag and WithRouter must produce correct state 'router'
        mock_cls: type[Tag] | type = type.__new__(mcs, _name, bases, {})

        initialized = _TAG_INITIALIZED  # As base classes is also declared here, we must be sure base class exists

        is_root = kwargs.get('_root')
        tag_name = '' if is_root else kwargs.get('name')
        namespace['__ROOT__'] = is_root

        if tag_name or (initialized and not hasattr(mock_cls, '_tag_name_')):
            namespace['_tag_name_'] = to_kebab_case(tag_name or _name)

        if 'raw_html' in kwargs:
            namespace['_raw_html'] = kwargs['raw_html']

        if 'force_ref' in kwargs:
            namespace['_force_ref'] = kwargs['force_ref']

        if 'mount' in kwargs:
            namespace['mount_element'] = kwargs['mount']

        if 'content_tag' in kwargs:
            content_tag = kwargs['content_tag']
            if isinstance(content_tag, str):
                content_tag = empty_tag(content_tag)()
            elif not isinstance(content_tag, Tag | NONE_TYPE):
                raise TypeError('content_tag argument must be either str, Tag or None')
            namespace['_content_tag'] = content_tag

        if 'children_tag' in kwargs:
            children_tag = kwargs['children_tag']
            if isinstance(children_tag, str):
                children_tag = empty_tag(children_tag)()
            elif not isinstance(children_tag, Tag):
                raise TypeError('children_tag argument must be either str or Tag')
            namespace['_static_children_tag'] = children_tag

        ref_children = []
        to_remove_children = []

        children_arg = namespace.get('children', [])
        if isinstance(children_arg, property):
            children_arg = []

        if children_arg:
            namespace.pop('children')
            children_arg = list(children_arg)
            if OVERWRITE not in children_arg and SUPER not in children_arg:
                children_arg.insert(0, SUPER)
        elif children_arg not in (None, False, []):
            namespace['_static_children'] = namespace.pop('children')
            children_arg = []

        if initialized:
            mcs._update_namespace_with_extra_attributes(namespace)

            for attribute_name, child in tuple(mcs._clean_namespace(namespace)):
                if callable(child) and hasattr(child, '_attrs_static_'):
                    continue

                if isinstance(child, Component | Children | ChildRef):
                    if child in children_arg:
                        ref_children.append(child)
                        # TODO: make possible inherit without replacement?
                        if (old_child := getattr(mock_cls, attribute_name, None)) and isinstance(old_child, ChildRef):
                            to_remove_children.append(old_child)
                        if isinstance(child, Component | Children):
                            children_arg[children_arg.index(child)] = namespace[attribute_name] = child.as_child(None)

                    if isinstance(child, Component) and child._force_ref:
                        # TODO: add support '_force_ref' for Children too
                        namespace[attribute_name] = _ref = child.as_child(None)
                        _ref.__set_name__(None, attribute_name)
                        children_arg.insert(0, _ref)
                        ref_children.append(_ref)

                    if isinstance(child, ChildRef) and child.child._force_ref:
                        children_arg.insert(0, child)
                        ref_children.append(child)

            for _index, child in enumerate(children_arg):
                if isinstance(child, str) and child not in _SPECIAL_CHILD_STRINGS:
                    children_arg[_index] = StringWrapper(child)

                if isinstance(child, Component) and child not in ref_children:
                    # TODO: replace 5 in get_random_name(5) with some log
                    children_arg[_index] = namespace[f'_{get_random_name(5)}_'] = child.as_child(None)

        cls: type[Tag] | type = super().__new__(mcs, _name, bases, namespace, **kwargs)

        if not hasattr(cls, '_raw_html'):
            cls._raw_html = False

        if initialized:
            cls._static_children = cls._static_children.copy()
            if not hasattr(cls, '_content_tag'):
                cls._content_tag = empty_div()
        else:
            cls._static_children = []

        if not hasattr(cls, '_static_children_tag'):
            cls._static_children_tag = None

        for child in to_remove_children:
            cls._static_children.remove(child)

        if getattr(cls, '_tag_name_', None) or not isinstance(getattr(cls, 'children', None), property):
            if children_arg:
                if CONTENT in children_arg and CONTENT in cls._static_children:
                    cls._static_children.remove(CONTENT)
                if SUPER in children_arg:
                    super_children_index = children_arg.index(SUPER)
                    children_arg[super_children_index : super_children_index + 1] = cls._static_children
                else:
                    children_arg.extend(cls._static_children)
                cls._static_children = children_arg
        else:
            cls._static_children = [CONTENT]

        cls._tags = []

        mcs._tag_classes.append(cls)

        if initialized and 'mount' in kwargs:
            cls._root_parent = None
            setattr(cls.mount_element, _PY_TAG_ATTRIBUTE, cls())

        if cls.__ROOT__:
            cls.__root_declared__()
        else:
            cls.__class_declared__()

        return cls

    @classmethod
    def __META_mount__(cls, self: Tag, args, kwargs, _original_func):
        self.__class__._tags.append(self)

        self._mount_finished_ = False

        result = _original_func(self, *args, **kwargs)

        self._mount_attrs()

        for child in self.children:
            if isinstance(child, CustomWrapper):
                child.__mount__(self.mount_element, self)
            elif isinstance(child, Mounter):
                child.__mount__(self._children_element, self)
            else:
                log.warn(f'Cannot mount: {child}')
        if self._children_tag:
            self.mount_element.insertChild(self._children_element)

        if self.content_child is None:
            _debugger(self)
        else:
            self.content_child._mount_children()

        super().__META_mount__(self, args, kwargs, None, _mount_attrs=False)

        self._mount_finished_ = True

        return result

    @classmethod
    def __META_render__(cls, self: Tag, args, kwargs, _original_func):
        if not self._mount_finished_ or (
            not self.mount_element.parentElement and self._root_parent != self  # dismounted
        ):
            return  # Prevent render before mount finished; Could be useful for setting intervals inside mount method

        return super().__META_render__(self, args, kwargs, _original_func)

    @classmethod
    def __META_init__(cls, self: Tag, args, kwargs, _original_func):  # noqa: PLR0912, PLR0915
        kwargs.pop('__parent__', None)  # called from clone
        if hasattr(getattr(self, 'mount_element', None), _PY_TAG_ATTRIBUTE):
            return

        self._children = self._static_children.copy()
        self._content = self._static_content

        children_argument: Callable | ContentType = kwargs.get('children') or args
        if children_argument and (not isinstance(children_argument, Iterable) or isinstance(children_argument, str)):
            children_argument = [children_argument]
        children_argument = list(children_argument)

        if children_argument:
            is_child_arg_string = False
            is_child_arg_function = False
            is_child_arg_tag = False
            try:
                content_empty = not bool(self.content())
            except Exception:  # noqa: BLE001 - trying to call content function
                content_empty = False
            if content_empty:
                is_child_arg_string = True
                is_child_arg_function = True
                is_child_arg_tag = True
                for index, child_arg in enumerate(children_argument):
                    if not isinstance(child_arg, str):
                        is_child_arg_string = False
                    if (isinstance(child_arg, type) and issubclass(child_arg, Tag)) or not callable(child_arg):
                        is_child_arg_function = False
                    if not isinstance(child_arg, Tag):
                        if isinstance(child_arg, str) and len(children_argument) > 1:
                            children_argument[index] = empty_span(child_arg)
                        else:
                            is_child_arg_tag = False

            if is_child_arg_string and children_argument:
                self._content = children_argument
            elif is_child_arg_function and children_argument and len(children_argument) == 1:
                self._content = MethodType(children_argument[0], self)
            elif is_child_arg_tag:
                self._children = self._children.copy() + [
                    child.clone(self).as_child(self) for child in children_argument
                ]
            else:
                self._children = [*self._children.copy(), *children_argument]

        for key, value in kwargs.items():
            if not isinstance(value, Component | Children) or key in self.attrs:
                continue
            value: Component | Children
            child = value.as_child(self, exists_ok=True)
            child.__set_name__(self, key)
            setattr(type(self), key, child)
            self._children.append(child)

        self._shadow_root = None
        self.mount_parent = None
        self._mount_finished_ = False

        if not hasattr(self, 'mount_element'):
            self.mount_element = js.document.createElement(self._tag_name_)
        if getattr(self.mount_element, _PY_TAG_ATTRIBUTE, None):
            raise ValueError(f'Coping or using as child is not allowed for "{self._tag_name_}"')
        else:
            setattr(self.mount_element, _PY_TAG_ATTRIBUTE, self)
        if self._static_children_tag:
            self._children_tag = self._static_children_tag.clone(self)
            self._children_element = self._children_tag.mount_element
            setattr(self._children_element, _PY_TAG_ATTRIBUTE, self)
        else:
            self._children_tag = None
            self._children_element = self.mount_element

        super().__META_init__(self, args, kwargs, _original_func)

    @classmethod
    def __META_unmount__(cls, self: Tag, args, kwargs, _original_func):
        if self in self.__class__._tags:  # But why?
            self.__class__._tags.remove(self)

        super().__META_unmount__(self, args, kwargs, None, _post_mount=False)

        for child in self.children:
            if isinstance(child, CustomWrapper):
                child.__unmount__(self.mount_element, self)
            elif isinstance(child, Mounter):
                child.__unmount__(self._children_element, self)
        if self._children_tag:
            self.mount_element.safeRemoveChild(self._children_element)

        result = _original_func(self, *args, **kwargs)

        self.post_unmount()

        return result


class Tag(Component, metaclass=_MetaTag, _root=True):
    # TODO: add docstrings

    __slots__ = (
        '_content',
        '_shadow_root',
        'mount_parent',
        '_mount_finished_',
        'mount_element',
        '_children',
        '_children_element',
        '_children_tag',
    )

    _root_parent: Tag = None  # see function mount in the bottom

    _static_content: ContentType = ''

    _content: ContentType
    _shadow_root: js.HTMLElement
    _ref: TagRef | None
    _force_ref: bool = False

    _tag_name_: str
    _tags: list[Tag]
    mount_element: js.HTMLElement
    mount_parent: js.HTMLElement
    _static_children: list[ContentType]
    _children: list[Mounter]
    _children_element: js.HTMLElement
    _static_children_tag: Tag
    _children_tag: Tag
    _mount_finished_: bool

    @classmethod
    def __root_declared__(cls):
        """This method is called, when root Tag is defined"""

    @classmethod
    def __class_declared__(cls):
        """This method is called, when common Tag is defined"""

    def __init__(self, *args, **kwargs: AttrType):
        kwargs.setdefault('_load_children', False)
        super().__init__(*args, **kwargs)

    def __new__(cls, *args, **kwargs):
        if hasattr(getattr(cls, 'mount_element', None), _PY_TAG_ATTRIBUTE):
            self = getattr(cls.mount_element, _PY_TAG_ATTRIBUTE)
        else:
            self = super().__new__(cls, *args, **kwargs)

        return self

    def __repr__(self):
        return f'{type(self).__name__}(<{self._tag_name_}/>, id#{self._id_})'

    def __hash__(self):
        # TODO: make force immutable this attributes
        return hash((self._tag_name_, self._id_))

    def __getitem__(self, key):
        return getattr(self, key)

    def as_child(self, parent: Tag | None, *, exists_ok=False, inline_def=False):
        if self._ref:
            if exists_ok:
                self.__set_ref__(parent, self._ref)
                return self._ref
            else:
                raise TypeError(f'Tag {self._tag_name_} already is child')
        ref = TagRef(self, inline_def=inline_def)
        self.__set_ref__(parent, ref)
        return ref

    def __notify__(self, attr_name: str, attribute: attr, value: AttrType):
        super().__notify__(attr_name, attribute, value)
        self.__render__()

    def __set_ref__(self, parent: Tag | None, ref: TagRef):
        super().__set_ref__(parent, ref)
        if ref.inline_def:
            setattr(type(parent), ref.name, self)

    def __render__(self, attrs: dict[str, AttrType] | None = None):
        self._current_render.append(self)

        if attrs is None:
            attrs = {}

        for name, value in {**self.__attrs__, **attrs}.items():
            # TODO: optimize this - set only changed attributes

            type = _attr.type if (_attr := self.attrs.get(name)) else NONE_TYPE
            set_html_attribute(self.mount_element, name, value, type=type)

        content_index = self.get_content_index()
        if content_index is not None:
            self.children[content_index].__render__()

        for index, child in enumerate(self.children):
            # TODO: optimize this - re-render the only children, that need this
            if isinstance(child, ChildRef):
                child.__render__(self)
            elif isinstance(child, CustomWrapper):
                if content_index is None or index != content_index:
                    child.__render__()
            elif isinstance(child, Renderer):
                child.__render__()
            else:  # string ?
                self._children_element.append(self._render(child))

        if self._current_render[-1] is self:
            self._current_render.pop()

    def content(self) -> ContentType:
        return self._content() if callable(self._content) else self._content

    def init(self, *args, _load_children=True, **kwargs):
        if _load_children:
            self.children = self.children.copy()

        for name, value in self.ref_children.items():
            if name not in kwargs:
                continue

            if isinstance(value, Children):
                getattr(self, name)[:] = kwargs[name]

        super().init(*args, **kwargs)

    def __mount__(self, element, parent: Tag, index=None):
        self.mount_parent = element

        super().__mount__(element, parent, index=index)

        self.mount_parent.insertChild(self.mount_element, index)

    def __unmount__(self, element, parent, *, _unsafe=False):
        if not _unsafe and self.mount_parent is not None and self.mount_parent is not element:
            log.warn(
                'Something went wrong!\n'
                f'Real parent: {self.mount_parent} {self.parent}. Passed parent: {element} {parent} '
                'If you override __mount__, you also should override __unmount__ too.'
            )
            log.warn(''.join(traceback.format_stack()[:-1]))

        (self.mount_parent or element).safeRemoveChild(self.mount_element)

    @property
    def own_children(self) -> list[Mounter]:
        return [child for child in self.children if not isinstance(child, ChildRef | CustomWrapper)]

    @property
    def ref_children(self) -> dict[str, Mounter]:
        return {child.name: child.__get__(self) for child in self.children if isinstance(child, ChildRef)}

    @property
    def content_child(self) -> ContentWrapper:
        for child in self.children:
            if isinstance(child, ContentWrapper) and child.content.__func__.__name__ == 'content':
                return child

    def get_content_index(self):
        for index, child in enumerate(self.children):
            if isinstance(child, ContentWrapper) and child.content.__func__.__name__ == 'content':
                return index

    @property
    def children(self) -> list[Mounter | Renderer | ChildRef | ContentWrapper]:
        return self._children

    @children.setter
    def children(self, children):
        self._children = self._handle_children(children)

    def _handle_children(self, children):
        result = []

        for new_child in children:
            child = new_child

            if isinstance(child, ContentWrapper):
                child = child.content.__func__
                if child.__name__ == 'content':
                    child = CONTENT

            if child == CONTENT:
                child = self.content

            if isinstance(child, attr):

                def child(s, _n=child.name):
                    return getattr(s, _n)

            if isinstance(child, Component) and child in self._children and child._ref is not None:
                # using Component as descriptor/just child; this allows save reference from parent to new copy of child
                child = child._ref._update_child(self, self._children.index(child))
            elif isinstance(child, ChildRef) and child in self._children:
                child._update_child(self, self._children.index(child))
            # TODO: make ContentWrapper descriptor, here call .clone()
            #  make possible to use ContentWrapper separately from function 'content'
            elif callable(child):
                if not isinstance(child, MethodType):
                    child = MethodType(child, self)
                child = ContentWrapper(child, self._content_tag, self._current_render)

            result.append(child)

        return result

    def clone(self, parent=None) -> Tag:
        clone = super().clone(parent=parent)
        clone._children = self.children
        return clone

    @property
    def _current_render(self):
        try:
            return _MetaTag._current_render[self._root_parent]
        except KeyError as e:
            _debugger(e)
            raise ValueError('It looks like element is not mounted correctly, please see the docs') from None


_TAG_INITIALIZED = True


@cache
def empty_tag(name):
    return _MetaTag(name, (Tag,), {}, name=name, content_tag=None)


def inline_tag(name, content_tag=None, **attributes):
    return _MetaTag(name, (Tag,), attributes, name=name, content_tag=content_tag)


empty_div = empty_tag('div')
empty_span = empty_tag('span')


def mount(element: Tag, root_element: str, *, clear=False):
    root = js.document.querySelector(root_element)
    if root is None:
        raise NameError('Mount point not found')

    js.beepy.stopLoading()
    if clear or js.beepy.dev_server.started:
        root.innerHTML = ''
    js.beepy.startLoading(mountPoint=root)

    parent = inline_tag(root.tagName.lower(), _root_parent=state(type=Tag, move_on=True))()
    parent._root_parent = parent
    parent._attrs_defaults['_root_parent'] = parent
    parent.__class__._root_parent.initial_value = parent
    parent.mount_element = root
    element.link_parent_attrs(parent)

    setattr(root, _PY_TAG_ATTRIBUTE, parent)
    _MetaTag._top_mount(element, root, parent)
    _MetaTag._top_render(element)

    if not js.document.title:
        js.document.title = 'BeePy'
        log.warn(f'Document title is not set, use default title: {js.document.title}')


__all__ = ['__version__', '_MetaTag', 'Tag', 'empty_tag', 'mount']
