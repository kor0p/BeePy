from __future__ import annotations

from collections import defaultdict
from typing import Union, Callable, Type, Iterable, Optional, get_type_hints
from types import MethodType
from functools import wraps

import js
import pyodide

from .attrs import attr, state, html_attr
from .children import ContentWrapper, ChildRef
from .listeners import on
from .types import Renderer, Mounter, AttrType, ContentType
from .utils import log, NONE_TYPE, __CONFIG__, _current, _debugger, to_kebab_case


__version__ = '0.1.3'


if pyodide.IN_BROWSER:
    __CONFIG__ = js.pyweb.__CONFIG__.to_py()
    js.Element.__str__ = lambda self: f'<{self.tagName.lower()}/>'


def _lifecycle_method(fn):
    name = fn.__name__
    attr_name = f'_wrapper_{name}_calling'
    _cache = _current['_lifecycle_method'][attr_name] = {}

    @wraps(fn)
    def lifecycle_method(original_func, *a, **kw):
        @wraps(original_func)
        def original_method_wrapper(self, *args, **kwargs):
            # prevent calling super() calls extra code twice
            _id = id(self)
            not_in_super_call = _id not in _cache

            if not_in_super_call:
                _cache[_id] = self

            result = fn(
                self, args, kwargs, *a, **kw, _original_func=original_func, _not_in_super_call=not_in_super_call
            )

            if not_in_super_call:
                del _cache[_id]

            return result
        return original_method_wrapper
    return lifecycle_method


_TAG_INITIALIZED = False


class _MetaTag(type):
    _tags = []

    def __new__(mcs, _name, bases, namespace, **kwargs):
        namespace = namespace.copy()
        log.debug('[__NAMESPACE__]', namespace)

        initialized = _TAG_INITIALIZED  # if class Tag is already defined

        is_root = kwargs.get('_root')
        if is_root:
            tag_name = ''
            namespace['__ROOT__'] = True
        else:
            tag_name = kwargs.get('name')

        if tag_name:
            namespace['_tag_name_'] = to_kebab_case(tag_name)

        if 'raw_html' in kwargs:
            namespace['_raw_html'] = kwargs['raw_html']

        if 'mount' in kwargs:
            namespace['mount_element'] = kwargs['mount']

        if 'content_tag' in kwargs:
            content_tag = kwargs['content_tag']
            if isinstance(content_tag, str):
                content_tag = empty_tag(content_tag)()
            elif not isinstance(content_tag, (Tag, NONE_TYPE)):
                raise TypeError('content_tag argument must be either str, Tag or None')
            namespace['_content_tag'] = content_tag

        if 'children_tag' in kwargs:
            children_tag = kwargs['children_tag']
            if isinstance(children_tag, str):
                children_tag = empty_tag(children_tag)()
            elif not isinstance(children_tag, Tag):
                raise TypeError('children_tag argument must be either str or Tag')
            namespace['children_tag'] = children_tag

        namespace['listeners'] = defaultdict(list)

        super_children_index = -1
        super_children = namespace.get('children', None)
        if isinstance(super_children, property):
            super_children = None

        if super_children:
            namespace.pop('children')
            super_children = list(super_children)
            if '__SUPER__' not in super_children:
                super_children.insert(0, '__SUPER__')
            super_children_index = super_children.index('__SUPER__')
        elif super_children is not None and super_children is not False:
            namespace['_static_children'] = namespace.pop('children')
            super_children = None

        if initialized:
            for attribute_name, child in tuple(namespace.items()):
                if attribute_name in ('_content_tag', 'children_tag',):
                    continue
                if isinstance(child, Tag):
                    # TODO: check existing attributes, that will be overwritten
                    # TODO: do this only if child is used in children = [] definition
                    namespace[attribute_name] = child.as_child_ref()

        try:
            cls: Union[Type[Tag], type] = super().__new__(mcs, _name, bases, namespace)
        except Exception as e:
            log.debug(e.__cause__, e)
            _debugger(e)
            raise e

        if not hasattr(cls, '_raw_html'):
            cls._raw_html = False

        if initialized and not hasattr(cls, '_content_tag'):
            cls._content_tag = empty_tag('div')()

        if not hasattr(cls, 'children_tag'):
            cls.children_tag = None

        if not initialized:
            cls._static_children = []

        if getattr(cls, '_tag_name_', None) or not isinstance(getattr(cls, 'children', None), property):
            if super_children:
                super_children = super_children.copy()
                super_children[super_children_index: super_children_index + 1] = cls._static_children
                cls._static_children = super_children
            else:
                cls._static_children = cls._static_children.copy()
        else:
            cls._static_children = ['__CONTENT__']

        cls._children = cls._static_children.copy()

        if initialized:
            cls._listeners = cls._listeners.copy()
            for _key, _value in cls.listeners.items():
                cls._listeners[_key].extend(_value)
        else:
            cls._listeners = defaultdict(list)

        if initialized:
            cls.attrs = cls.attrs.copy()
        else:
            cls.attrs = {}

        if initialized:
            for name, attribute in namespace.items():
                if isinstance(attribute, attr):
                    attribute.__set_to_tag__(name, cls)

        mcs._tags.append(cls)

        if '__mount__' in namespace:
            cls.__mount__ = mcs.__mount(cls.__mount__)

        if '__render__' in namespace:
            cls.__render__ = mcs.__render(cls.__render__)

        if '__init__' in namespace:
            cls.__init__ = mcs.__init(cls.__init__)

        if initialized and 'mount' in kwargs:
            cls.mount_element._py = cls()

        return cls

    @classmethod
    def _resolve_annotations(mcs):
        for cls in mcs._tags:
            for name, _type in get_type_hints(cls).items():
                if not (attribute := getattr(cls, name, None)) or not isinstance(attribute, attr):
                    continue

                attribute.__set_type__(_type)

    @classmethod
    def _pre_top_mount(mcs):
        mcs._resolve_annotations()

    @_lifecycle_method
    def __mount(self: Tag, args, kwargs, _original_func, _not_in_super_call):
        log.debug('[__MOUNT__]', self, args, kwargs, _original_func, _not_in_super_call, args[0]._py)

        if _not_in_super_call:
            self.pre_mount()

        result = _original_func(self, *args, **kwargs)

        if _not_in_super_call:
            for child in self.children:
                if isinstance(child, ChildRef):
                    child.__mount__(self)
                elif isinstance(child, ContentWrapper):
                    child.__mount__(self.mount_element)
                elif isinstance(child, Mounter):
                    child.__mount__(self.children_element)
                elif not isinstance(child, str):
                    log.warn(f'Cannot mount: {child}')
            if self.children_tag:
                self.mount_element.insertChild(self.children_element)

            content = self.content()

            if isinstance(content, Tag):
                content = (content,)
            elif isinstance(content, Iterable) and not isinstance(content, str) and content:
                content = list(content)
                for _child in content[:]:
                    if not isinstance(_child, Tag):
                        content = None
                        break
            else:
                content = None

            if content:
                content_children = self.content_children
                for child in content:
                    child.__mount__(content_children.mount_element)
                content_children.children = content

            for name, attribute in self.__states__.items():
                if callable(attribute) and not isinstance(attribute, MethodType):
                    setattr(self, name, MethodType(attribute, self.parent))
            for event, listeners in self._listeners.items():
                for listener in listeners:
                    listener._add_listener(event, self)
            self.mount()

        return result

    @_lifecycle_method
    def __render(self: Tag, args, kwargs, _original_func, _not_in_super_call):
        _current['render'].append(self)
        _current['rerender'].append(self)

        if _not_in_super_call:
            self.pre_render()

        result = _original_func(self, *args, **kwargs)

        if _current['render'][-1] is self:
            _current['render'].pop()

        if _not_in_super_call:
            self.render()

        return result

    @_lifecycle_method
    def __init(self: Tag, args, kwargs, _original_func, _not_in_super_call):
        if hasattr(getattr(self, 'mount_element', None), '_py'):
            return

        if _not_in_super_call:
            children_argument: Union[Callable, ContentType] = kwargs.get('children') or args
            if children_argument and (not isinstance(children_argument, Iterable) or isinstance(children_argument, str)):
                children_argument = (children_argument,)
            if children_argument:
                is_child_arg_string = False
                is_child_arg_function = False
                try:
                    content_empty = not bool(self.content())
                except Exception as e:
                    content_empty = False
                if content_empty:
                    is_child_arg_string = True
                    is_child_arg_function = True
                    for child_arg in children_argument:
                        if not isinstance(child_arg, str):
                            is_child_arg_string = False
                        if not isinstance(child_arg, Callable):
                            is_child_arg_function = False
                if is_child_arg_string and children_argument:
                    self._content = children_argument
                elif is_child_arg_function and children_argument and len(children_argument) == 1:
                    self.content = MethodType(children_argument[0], self)
                else:
                    self._children = self._children.copy() + [*children_argument]
            self._args = args
            self._kwargs = kwargs
            self._dependents = []
            if not hasattr(self, 'mount_element'):
                self.mount_element = js.document.createElement(self._tag_name_)
            if getattr(self.mount_element, '_py', None):
                raise ValueError(f'Coping or using as child is not allowed for "{self._tag_name_}"')
            else:
                self.mount_element._py = self
            if self.children_tag:
                self.children_tag = self.children_tag.clone()
                self.children_element = self.children_tag.mount_element
                self.children_element._py = self
            else:
                self.children_element = self.mount_element
            self.children = self.children.copy()
            self.listeners = self.listeners.copy()
            for event, listeners in self.listeners.items():
                self.listeners[event] = listeners.copy()
            self._listeners = self._listeners.copy()
            for event, listeners in self._listeners.items():
                self._listeners[event] = listeners.copy()

        _original_func(self, *args, **kwargs)

        if _not_in_super_call:
            pass  # for future


class Tag(Renderer, Mounter, metaclass=_MetaTag, _root=True):
    _content: ContentType = ''
    _dependents: list[Tag, ...]
    _args: tuple[AttrType, ...]
    _kwargs: dict[str, AttrType]
    _ref: Optional[ChildRef] = None

    _tag_name_: str
    attrs: dict[str, attr]
    listeners: defaultdict[str, list[on, ...]]
    _listeners: defaultdict[str, list[on, ...]]
    mount_element: js.HTMLElement
    mount_parent: js.HTMLElement
    parent: Optional[Tag]
    content: Union[ContentType, Callable[[Tag], ContentType]]
    _static_children: list[ContentType, ...]
    _children: list[Mounter, ...]
    children_element: js.HTMLElement
    children_tag: Tag

    def __init__(self, *args, **kwargs: AttrType):
        for key, _attr in self.attrs.items():
            if key not in kwargs:
                if _attr.required:
                    raise TypeError(f'Attribute {_attr.name!r} is required')
                continue

            value = kwargs[key]

            setattr(self, key, value)

    def __new__(cls, *args, **kwargs):
        if hasattr(getattr(cls, 'mount_element', None), '_py'):
            return cls.mount_element._py
        return super().__new__(cls)

    def __repr__(self):
        return f'{type(self).__name__}(<{self._tag_name_}/>)'

    def __html__(self, children=None) -> str:
        attrs = ''
        for key, value in self.__attrs__.items():
            if isinstance(value, bool):
                if value:
                    attrs += key + ' '
                continue
            attrs += f'{key}="{value}" '
        if attrs:
            attrs = attrs[:-1]  # pop last ' '
        if not children:
            children = ''.join(getattr(child, '__html__', child.__str__)() for child in self.own_children)
        if children:
            return f'<{self._tag_name_} {attrs}>{self._render(children)}</{self._tag_name_}>'
        return f'<{self._tag_name_} {attrs} />'

    @classmethod
    def comment(cls, string) -> str:
        return f'<!-- {string} -->'

    @property
    def __attrs__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr.__get_view_value__(self)
            for _attr in self.attrs.values()
            if _attr._view
        }

    @property
    def __states__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr.__get__(self)
            for _attr in self.attrs.values()
        }

    def as_child_ref(self):
        if self._ref:
            raise TypeError(f'Tag {self._tag_name_} already is child')
        ref = ChildRef(self)
        self.__set_ref__(ref)
        return ref

    def __set_ref__(self, ref: ChildRef):
        self._ref = ref

    def pre_render(self):
        """empty method for easy override with code for run before render"""

    def __render__(self, attrs: Optional[dict[str, AttrType]] = None):
        if attrs is None:
            attrs = {}

        for name, value in {**self.__attrs__, **attrs}.items():
            # TODO: optimize this - set only changed attributes
            if getattr(self.mount_element.attributes, name, None) and value is None:
                self.mount_element.removeAttribute(name)
            elif value is not None:
                self.mount_element.setAttribute(name, value)

        content_index = self.get_content_index()
        if content_index is not None:
            self.children[content_index].__render__()

        for index, child in enumerate(self.children):
            # TODO: optimize this - re-render the only children, that need this
            if isinstance(child, ChildRef):
                child.__render__(self)
            elif isinstance(child, ContentWrapper):
                if content_index is None or index != content_index:
                    child.__render__()
            elif isinstance(child, Renderer):
                child.__render__()
            else:  # string ?
                self.children_element.append(self._render(child))

    def render(self):
        """empty method for easy override with code for run after render"""

    def content(self) -> str:
        return self._content

    def pre_mount(self):
        """empty method for easy override with code for run before mount"""

    def __mount__(self, element, index=None):
        self.parent = element._py
        self.mount_parent = element
        self.mount_parent.insertChild(self.mount_element, index)

    def mount(self):
        """empty method for easy override with code for run after mount"""

    @property
    def own_children(self) -> list[Mounter, ...]:
        return [child for child in self.children if not isinstance(child, (ChildRef, ContentWrapper))]

    @property
    def ref_children(self) -> dict[str, Mounter]:
        return {child.name: child.__get__(self) for child in self.children if isinstance(child, ChildRef)}

    @property
    def content_children(self) -> Tag:
        index = self.get_content_index()
        if index is not None:
            return self.children[index]

    def get_content_index(self):
        for index, child in enumerate(self.children):
            if isinstance(child, ContentWrapper) and child.content.__func__.__name__ == 'content':
                return index

    @property
    def children(self) -> list[Union[Mounter, Renderer], ...]:
        return self._children

    @children.setter
    def children(self, children):
        self._children = self._handle_children(children)

    def _handle_children(self, children):
        result = []

        for child in children:
            result.append(child)

            if isinstance(child, ContentWrapper):
                child = child.content.__func__

            if child == '__CONTENT__':
                child = self.content
                if not callable(child):
                    _content = child
                    child = MethodType(lambda s: _content, self)

            if isinstance(child, ChildRef) and child in self._children:
                # special case for wrapped Tag - generated when using Tag as descriptor
                # this allows save reference from parent to new copy of child
                child._update_child(self, self._children.index(child))
            elif isinstance(child, Tag):
                result[-1] = child = child.clone()
            elif callable(child):
                if not isinstance(child, MethodType):
                    child = MethodType(child, self)
                result[-1] = child = ContentWrapper(child, self._content_tag)
            elif isinstance(child, str):
                continue

        return result

    # descriptor part
    def __get__(self, instance, owner):
        return self

    def clone(self) -> Tag:
        clone = type(self)(*self._args, **self._kwargs)
        clone.children = self.children
        clone._listeners = self._listeners.copy()
        for event, listeners in clone._listeners.items():
            clone._listeners[event] = listeners.copy()
        return clone

    def on(self, method=None):
        def wrapper(callback):
            event_listener = on(method)(callback, get_parent=True)
            event_name = event_listener.name or callback.__name__
            setattr(self, event_name, event_listener.__get__(self))
            event_listener.__set_name__(self, event_name)
            self._listeners[event_listener.name] = self._listeners[event_listener.name].copy() + [event_listener]
        if not isinstance(method, str):
            return wrapper(method)
        return wrapper


_TAG_INITIALIZED = True


def empty_tag(name):
    return _MetaTag(name, (Tag, ), {}, name=name, content_tag=None)


def mount(element: Tag, root_element: str):
    _MetaTag._pre_top_mount()
    parent = js.document.querySelector(root_element)
    if parent is None:
        raise NameError('Mount point not found')
    parent._py = None
    element.__mount__(parent)
    element.__render__()


__all__ = ['__version__', '_debugger', 'attr', 'state', 'html_attr', '_MetaTag', 'Tag', 'on', 'empty_tag', 'mount']
