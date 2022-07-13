from __future__ import annotations

from collections import defaultdict
from typing import Union, Callable, Type, Any, Iterable, Optional
from types import MethodType
from functools import wraps, partial

import js
import pyodide

from .attrs import attr, state, html_attr
from .children import ContentWrapper, ChildRef, TagRef, Children
from .listeners import on
from .types import Renderer, Mounter, WebBase, AttrType, ContentType
from .utils import (
    log, NONE_TYPE, __CONFIG__, _current, _debugger, get_random_name, to_kebab_case,
)
from .context import _MetaContext, Context


__version__ = '0.2.0'


if pyodide.IN_BROWSER:
    js.Element.__str__ = lambda self: f'<{self.tagName.lower()}/>'


def _lifecycle_method(*, hash_function=hash):
    def _wrapper(fn):
        name = fn.__name__
        attr_name = f'_wrapper_{name}_calling'
        _cache = _current['_lifecycle_method'][attr_name] = {}

        @wraps(fn)
        def lifecycle_method(original_func):
            @wraps(original_func)
            def original_method_wrapper(self, *args, **kwargs):
                # prevent calling super() calls extra code twice
                _hash = hash_function(self)
                not_in_super_call = _hash not in _cache

                if not_in_super_call:
                    _cache[_hash] = self
                    result = fn(self, args, kwargs, _original_func=original_func)
                    del _cache[_hash]
                else:
                    result = original_func(self, *args, **kwargs)

                return result
            return original_method_wrapper
        return lifecycle_method
    return _wrapper


_TAG_INITIALIZED = False


class _MetaTag(_MetaContext):
    _tag_classes: list[Type[Tag], ...] = []
    __clean_class_attribute_names = ('_content_tag', 'static_children_tag')

    def __new__(mcs, _name: str, bases: tuple, namespace: dict, **kwargs):
        # TODO: create decorator for functions like this:
        # @tag
        # def test_tag(self: Tag, counter: int = 0):
        #     @self.on
        #     def click(event):
        #         self.counter += 1
        #
        #     @self.renderer
        #     def content():
        #         return f'Counter: {self.counter}'

        namespace = namespace.copy()
        namespace.setdefault('__slots__', ())
        if '_content' in namespace:
            namespace['_static_content'] = namespace.pop('_content')
        log.debug('[__NAMESPACE__]', namespace)

        # used for checking inheritance: attributes, methods, etc
        base_cls: Union[Type[Tag], type] = type.__new__(mcs, _name, bases, {})

        initialized = _TAG_INITIALIZED  # if class Tag is already defined

        is_root = kwargs.get('_root')
        if is_root:
            tag_name = ''
        else:
            tag_name = kwargs.get('name')
        namespace['__ROOT__'] = is_root

        if tag_name:
            namespace['_tag_name_'] = to_kebab_case(tag_name)

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
            elif not isinstance(content_tag, (Tag, NONE_TYPE)):
                raise TypeError('content_tag argument must be either str, Tag or None')
            namespace['_content_tag'] = content_tag

        if 'children_tag' in kwargs:
            children_tag = kwargs['children_tag']
            if isinstance(children_tag, str):
                children_tag = empty_tag(children_tag)()
            elif not isinstance(children_tag, Tag):
                raise TypeError('children_tag argument must be either str or Tag')
            namespace['static_children_tag'] = children_tag

        ref_children = []
        to_remove_children = []
        static_onchange_handlers = []

        super_children_index = -1
        children_arg = namespace.get('children', [])
        if isinstance(children_arg, property):
            children_arg = []

        if children_arg:
            namespace.pop('children')
            children_arg = list(children_arg)
            if '__SUPER__' not in children_arg:
                children_arg.insert(0, '__SUPER__')
            super_children_index = children_arg.index('__SUPER__')
        elif children_arg not in (None, False, []):
            namespace['_static_children'] = namespace.pop('children')
            children_arg = []

        if initialized:
            for attribute_name, child in tuple(mcs._clean_namespace(namespace)):
                if callable(child) and hasattr(child, '_attrs_static_'):
                    _states_with_static_handler = defaultdict(list)
                    for trigger, _states in child._attrs_static_.items():
                        for _state in _states:
                            _states_with_static_handler[trigger].append(_state)
                            _state.handlers[trigger].remove(child)
                    static_onchange_handlers.append((child, _states_with_static_handler))

                if isinstance(child, (Tag, Children, ChildRef)):
                    if child in children_arg:
                        ref_children.append(child)
                        # TODO: make possible inherit without replacement?
                        if (old_child := getattr(base_cls, attribute_name, None)) and isinstance(old_child, ChildRef):
                            to_remove_children.append(old_child)
                        if isinstance(child, (Tag, Children)):
                            children_arg[children_arg.index(child)] = namespace[attribute_name] = child.as_child()
    
                    if isinstance(child, Tag) and child._force_ref:  # TODO: add support '_force_ref' for Children too
                        namespace[attribute_name] = child.as_child()
                        children_arg.append(namespace[attribute_name])

            for child in children_arg:
                if isinstance(child, Tag) and child not in ref_children:
                    children_arg[children_arg.index(child)] = namespace[f'_{get_random_name(5)}_'] = child.as_child()

        cls: Union[Type[Tag], type] = super().__new__(mcs, _name, bases, namespace, **kwargs)

        if not hasattr(cls, '_raw_html'):
            cls._raw_html = False

        if initialized and not hasattr(cls, '_content_tag'):
            cls._content_tag = empty_tag('div')()

        if not hasattr(cls, 'static_children_tag'):
            cls.static_children_tag = None

        if initialized:
            cls._static_children = cls._static_children.copy()
        else:
            cls._static_children = []

        for child in to_remove_children:
            cls._static_children.remove(child)

        if getattr(cls, '_tag_name_', None) or not isinstance(getattr(cls, 'children', None), property):
            if children_arg:
                children_arg[super_children_index: super_children_index + 1] = cls._static_children
                cls._static_children = children_arg
        else:
            cls._static_children = ['__CONTENT__']

        if initialized:
            cls.static_listeners = cls.static_listeners.copy()
            for key, value in cls.static_listeners.items():
                cls.static_listeners[key] = value.copy()
        else:
            cls.static_listeners = defaultdict(list)

        if initialized:
            cls._static_onchange_handlers = cls._static_onchange_handlers.copy() + static_onchange_handlers
        else:
            cls._static_onchange_handlers = []

        cls._tags = []

        mcs._tag_classes.append(cls)

        if '__mount__' in namespace:
            cls.__mount__ = mcs.__mount(cls.__mount__)

        if '__render__' in namespace:
            cls.__render__ = mcs.__render(cls.__render__)

        if '__init__' in namespace:
            cls.__init__ = mcs.__init(cls.__init__)

        if '__unmount__' in namespace:
            cls.__unmount__ = mcs.__unmount(cls.__unmount__)

        if initialized and 'mount' in kwargs:
            cls.mount_element._py = cls()

        if cls.__ROOT__:
            cls.__root_declared__()
        else:
            cls.__class_declared__()

        return cls

    @_lifecycle_method()
    def __mount(self: Tag, args, kwargs, _original_func):
        log.debug('[__MOUNT__]', self, args, kwargs, _original_func, *args)

        self._mount_attrs()

        result = _original_func(self, *args, **kwargs)

        for child in self.children:
            if isinstance(child, ContentWrapper):
                child.__mount__(self.mount_element, self)
            elif isinstance(child, Mounter):
                child.__mount__(self.children_element, self)
            elif not isinstance(child, str):
                log.warn(f'Cannot mount: {child}')
        if self.children_tag:
            self.mount_element.insertChild(self.children_element)

        self.content_child._mount_children()

        for name, attribute in self.__states__.items():
            if callable(attribute) and not isinstance(attribute, MethodType):
                setattr(self, name, MethodType(attribute, self.parent))

        for event, listeners in self.listeners.items():
            for listener in listeners:
                self._event_listeners[event].append(
                    listener._make_listener(event, self)
                )

        for onchange_handler, _states_with_static_handler in self._static_onchange_handlers:
            for trigger, _states in _states_with_static_handler.items():
                for _state in _states:
                    # TODO: can we save order of triggers' call?
                    _state.handlers[trigger].append(MethodType(onchange_handler, self))

        self.mount()

        return result

    @_lifecycle_method()
    def __render(self: Tag, args, kwargs, _original_func):
        # TODO: maybe function 'render' could return some content, appended to args?
        self.render()

        _original_func(self, *args, **kwargs)

        self.post_render()

    @_lifecycle_method(hash_function=id)
    def __init(self: Tag, args, kwargs, _original_func):
        self.__class__._tags.append(self)
        if hasattr(getattr(self, 'mount_element', None), '_py'):
            return

        self._children = self._static_children.copy()
        self._content = self._static_content

        children_argument: Union[Callable, ContentType] = kwargs.get('children') or args
        if children_argument and (not isinstance(children_argument, Iterable) or isinstance(children_argument, str)):
            children_argument = (children_argument,)
        if children_argument:
            is_child_arg_string = False
            is_child_arg_function = False
            is_child_arg_tag = False
            try:
                content_empty = not bool(self.content())
            except Exception as e:
                content_empty = False
            if content_empty:
                is_child_arg_string = True
                is_child_arg_function = True
                is_child_arg_tag = True
                for child_arg in children_argument:
                    if not isinstance(child_arg, str):
                        is_child_arg_string = False
                    if (isinstance(child_arg, type) and issubclass(child_arg, Tag)) or not callable(child_arg):
                        is_child_arg_function = False
                    if not isinstance(child_arg, Tag):
                        is_child_arg_tag = False

            if is_child_arg_string and children_argument:
                self._content = children_argument
            elif is_child_arg_function and children_argument and len(children_argument) == 1:
                self._content = MethodType(children_argument[0], self)
            elif is_child_arg_tag:
                self._children = self._children.copy() + [child.clone().as_child() for child in children_argument]
            else:
                self._children = self._children.copy() + [*children_argument]

        self._dependents = []
        self._shadow_root = None

        if not hasattr(self, 'mount_element'):
            self.mount_element = js.document.createElement(self._tag_name_)
        if getattr(self.mount_element, '_py', None):
            raise ValueError(f'Coping or using as child is not allowed for "{self._tag_name_}"')
        else:
            self.mount_element._py = self
        if self.static_children_tag:
            self.children_tag = self.static_children_tag.clone()
            self.children_element = self.children_tag.mount_element
            self.children_element._py = self
        else:
            self.children_tag = None
            self.children_element = self.mount_element

        self.children = self.children.copy()

        self.listeners = self.static_listeners.copy()
        for event, listeners in self.listeners.items():
            self.listeners[event] = listeners.copy()

        self._event_listeners = defaultdict(list)
        self.handlers = defaultdict(list)

        _original_func(self, *args, **kwargs)

    @_lifecycle_method()
    def __unmount(self: Tag, args, kwargs, _original_func):
        log.debug('[__UNMOUNT__]', self, args, kwargs, _original_func, args[0]._py)

        self.unmount()

        for child in self.children:
            if isinstance(child, ContentWrapper):
                child.__unmount__(self.mount_element, self)
            elif isinstance(child, Mounter):
                child.__unmount__(self.children_element, self)
        if self.children_tag:
            self.mount_element.safeRemoveChild(self.children_element)

        result = _original_func(self, *args, **kwargs)

        if pyodide.IN_BROWSER:
            for event, proxies in self._event_listeners.items():
                for proxy in proxies:
                    proxy.__on__._unlink_listener(proxy)
                    self.mount_element.removeEventListener(event, proxy)
                    proxy.destroy()

        self.post_unmount()

        return result


class Tag(WebBase, Context, metaclass=_MetaTag, _root=True):
    __slots__ = (
        '_content', '_dependents', '_shadow_root', '_ref',
        'listeners', '_event_listeners',
        'mount_parent', 'parent',
        'mount_element', '_children', 'children_element', 'children_tag',
        'handlers',
    )

    _static_content: ContentType = ''

    _content: ContentType
    _dependents: list[Tag, ...]
    _shadow_root: js.HTMLElement
    _ref: Optional[TagRef]
    _force_ref: bool = False

    _tag_name_: str
    _tags: list[Tag, ...]
    static_listeners: defaultdict[str, list[on, ...]]
    listeners: defaultdict[str, list[on, ...]]
    _event_listeners: defaultdict[str, list[pyodide.JsProxy, ...]]
    mount_element: js.HTMLElement
    mount_parent: js.HTMLElement
    parent: Optional[Tag]
    _static_children: list[ContentType, ...]
    _children: list[Mounter, ...]
    children_element: js.HTMLElement
    static_children_tag: Tag
    children_tag: Tag
    handlers: defaultdict[str, list[Callable[[Tag, js.Event, str, Any], None], ...]]
    _static_onchange_handlers: list[tuple[Callable[[Tag, Any], Any], dict[str, list[state, ...]]]]

    @classmethod
    def __root_declared__(cls):
        """ This method is called, when root Tag is defined """

    @classmethod
    def __class_declared__(cls):
        """ This method is called, when common Tag is defined """

    def __init__(self, *args, **kwargs: AttrType):
        super().__init__(*args, **kwargs)
        self._ref = None
        for name, value in self.ref_children.items():
            if name not in kwargs:
                continue

            if isinstance(value, Children):
                getattr(self, name)[:] = kwargs[name]

    def __new__(cls, *args, **kwargs):
        if hasattr(getattr(cls, 'mount_element', None), '_py'):
            self = cls.mount_element._py
        else:
            self = super().__new__(cls, *args, **kwargs)

        return self

    def __repr__(self):
        return f'{type(self).__name__}(<{self._tag_name_}/>)'

    def __hash__(self):
        # TODO: make force immutable this attributes
        return hash((self._tag_name_, self._id_))

    @classmethod
    def comment(cls, string) -> str:
        return f'<!-- {string} -->'

    def as_child(self, exists_ok=False):
        if self._ref:
            if exists_ok:
                return self._ref
            else:
                raise TypeError(f'Tag {self._tag_name_} already is child')
        ref = TagRef(self)
        self.__set_ref__(ref)
        return ref

    def __notify__(self, attr_name: str, attribute: attr, value: AttrType):
        super().__notify__(attr_name, attribute, value)
        self.__render__()

    def __set_ref__(self, ref: TagRef):
        self._ref = ref

    def render(self):
        """empty method for easy override with code for run before render"""

    def __render__(self, attrs: Optional[dict[str, AttrType]] = None):
        _current['render'].append(self)
        _current['rerender'].append(self)

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

        if _current['render'][-1] is self:
            _current['render'].pop()

    def post_render(self):
        """empty method for easy override with code for run after render"""

    def content(self) -> ContentType:
        return self._content() if callable(self._content) else self._content

    def _mount_attrs(self):
        for attribute in self.attrs.values():
            attribute.__mount_tag__(self)

    def pre_mount(self):
        """empty method for easy override with code for run before mount"""

    def __mount__(self, element, parent: Tag, index=None):
        self.parent = parent
        self.mount_parent = element
        self.pre_mount()
        self.mount_parent.insertChild(self.mount_element, index)

    def mount(self):
        """empty method for easy override with code for run after mount"""

    def unmount(self):
        """empty method for easy override with code for run before unmount"""

    def __unmount__(self, element, parent):
        if self.mount_parent is not element:
            return

        element.safeRemoveChild(self.mount_element)

    def post_unmount(self):
        """empty method for easy override with code for run after unmount"""

    @property
    def own_children(self) -> list[Mounter, ...]:
        return [child for child in self.children if not isinstance(child, (ChildRef, ContentWrapper))]

    @property
    def ref_children(self) -> dict[str, Mounter]:
        return {child.name: child.__get__(self) for child in self.children if isinstance(child, ChildRef)}

    @property
    def content_child(self) -> ContentWrapper:
        index = self.get_content_index()
        if index is not None:
            return self.children[index]

    def get_content_index(self):
        for index, child in enumerate(self.children):
            if isinstance(child, ContentWrapper) and child.content.__func__.__name__ == 'content':
                return index

    @property
    def children(self) -> list[Union[Mounter, Renderer, ChildRef], ...]:
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
                # TODO: check for 'content' function inheritance
                child = self.content

            if isinstance(child, attr):
                _state_name = child.name
                child = lambda s: getattr(s, _state_name)

            if isinstance(child, Tag) and child in self._children:
                # using Tag as descriptor/just child; this allows save reference from parent to new copy of child
                child._ref._update_child(self, self._children.index(child))
            elif isinstance(child, ChildRef) and child in self._children:
                child._update_child(self, self._children.index(child))
            # TODO: make ContentWrapper descriptor, here call .clone()
            #  make possible to use ContentWrapper separately from function 'content'
            elif callable(child):
                if not isinstance(child, MethodType):
                    child = MethodType(child, self)
                result[-1] = ContentWrapper(child, self._content_tag)

        return result

    # descriptor part
    def __get__(self, instance, owner):
        return self

    def clone(self) -> Tag:
        clone = super().clone()
        # TODO: create list of arguments to copy, instead of part below
        clone.children = self.children
        clone.listeners = self.listeners.copy()
        for event, listeners in clone.listeners.items():
            clone.listeners[event] = listeners.copy()
        clone.handlers = self.handlers.copy()
        for event, handlers in clone.handlers.items():
            clone.handlers[event] = handlers.copy()
        return clone

    def on(self, method=None):
        if isinstance(method, str) and method.startswith(':'):
            action = method[1:]

            def wrapper(handler, action_name=None):
                if action_name is None:
                    action_name = handler.__name__

                self.handlers[action_name].append(handler)
                return handler

            if action:
                return partial(wrapper, action_name=action)

            return wrapper

        def wrapper(callback):
            event_listener = on(method)(callback, get_parent=True)
            event_name = event_listener.name or callback.__name__
            event_listener.__set_name__(self, event_name, set_static_listeners=False)
            self.listeners[event_name] = self.listeners[event_name].copy() + [event_listener]
            return event_listener.__get__(self)

        if not isinstance(method, str):
            return wrapper(method)

        return wrapper


_TAG_INITIALIZED = True


def empty_tag(name):
    return _MetaTag(name, (Tag, ), {}, name=name, content_tag=None)


def mount(element: Tag, root_element: str):
    # TODO: pyweb.createRoot?
    _MetaTag._pre_top_mount()
    root = js.document.querySelector(root_element)
    if root is None:
        raise NameError('Mount point not found')
    parent = empty_tag(root.tagName)()
    root._py = parent
    element.__mount__(root, parent)
    _current['render'] = []
    element.__render__()


__all__ = [
    '__version__', '__CONFIG__', '_debugger', 'attr', 'state', 'html_attr', '_MetaTag', 'Tag', 'on', 'empty_tag',
    'mount',
]
