from __future__ import annotations as _

import traceback
from collections import defaultdict
from typing import Union, Callable, Any, Type, Iterable, Optional, SupportsIndex, get_type_hints
from types import MethodType
from functools import wraps, partial
import inspect

import js
import pyodide

from .utils import to_kebab_case, js_func


__version__ = '0.1.2b'
__CONFIG__ = {
    'debug': True,
    'path': '..',
    'modules': ['utils.py', 'framework.py', 'style.py', 'tags.py'],
}


if pyodide.IN_BROWSER:
    __CONFIG__ = js.pyweb.__CONFIG__.to_py()
    js.Element.__str__ = lambda self: f'<{self.tagName.lower()}/>'


async def delay(ms):
    return await js.delay(ms)


def _debugger(error=None):
    log.warn('\n'.join(traceback.format_stack()[0 if error else 5:]))
    js._locals = pyodide.to_js(inspect.currentframe().f_back.f_locals, dict_converter=js.Object.fromEntries)
    js._DEBUGGER(error)


AttrType = Union[None, str, int, bool, Iterable['AttrType'], dict[str, 'AttrType'], 'Tag']
ContentType = Union[str, Iterable, 'Renderer']


_current_render: list[Renderer, ...] = []
_current_rerender: list[Renderer, ...] = []
_current__lifecycle_method: dict[str, dict[int, Tag]] = {}
_current: dict[str, Any] = {
    'render': _current_render,
    'rerender': _current_rerender,
    '_lifecycle_method': _current__lifecycle_method,
}


log = js.console


class AttrValue:
    """
    Extend this class to be able to use it as value in pyweb.attr and children
    """

    def __view_value__(self):
        """ This method will be called on render, must return serializable value """
        raise NotImplementedError


NONE_TYPE = type(None)


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
        return f'{self.name}({self.value!r})'

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

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return getattr(instance.mount_element, self.name, None)

    def __set__(self, instance, value):
        if isinstance(instance, Tag):
            # TODO: attributes is set like setAttribute, but why?
            setattr(instance.mount_element, self.name, value)

    def __del__(self, instance):
        delattr(instance.mount_element, self.name)


class html_state(html_attr):
    __slots__ = ()

    _view = False


class Trackable:
    def onchange(self):
        pass

    def _notify_add_one(self, key: int, added):
        raise NotImplementedError

    def _notify_remove_one(self, key: int, to_remove):
        raise NotImplementedError

    def _notify_add(self, key: Union[SupportsIndex, slice], added):
        raise NotImplementedError

    def _notify_remove(self, key: Union[SupportsIndex, slice], to_remove):
        raise NotImplementedError


class TrackableList(Trackable, list):
    def _notify_add(self, key: Union[SupportsIndex, slice], added: Union[tuple, list]):
        if isinstance(key, slice):
            for index, value in zip(range(key.start or 0, key.stop or len(self), key.step or 1), added):
                if index < 0:
                    index += len(self)
                self._notify_add_one(index, value)
        else:
            index = key.__index__()
            if index < 0:
                index += len(self)
            self._notify_add_one(index, added[0])
        self.onchange()

    def _notify_remove(self, key: Union[SupportsIndex, slice], to_remove: Union[tuple, list]):
        if isinstance(key, slice):
            for index, value in reversed(list(
                zip(range(key.start or 0, key.stop or len(self), key.step or 1), to_remove)
            )):
                if index < 0:
                    index += len(self)
                self._notify_remove_one(index, value)
        else:
            index = key.__index__()
            if index < 0:
                index += len(self)
            self._notify_remove_one(index, to_remove[0])
        self.onchange()

    def append(self, __object):
        super().append(__object)
        self._notify_add(-1, (self[-1], ))

    def clear(self):
        self._notify_remove(slice(0, len(self)), self)
        super().clear()

    def extend(self, __iterable):
        length = len(self)
        super().extend(__iterable)
        self._notify_add(slice(length, len(self)), self[length:len(self)])

    def insert(self, __index, __object):
        index = __index.__index__()
        super().insert(index, __object)
        self._notify_add(index, (self[index], ))

    def pop(self, __index=None):
        if __index is None:
            index = len(self) - 1
        else:
            index = __index.__index__()

        self._notify_remove(index, (self[index], ))
        super().pop(__index)

    def remove(self, __value):
        self._notify_remove(self.index(__value), (__value, ))
        super().remove(__value)

    def reverse(self):
        raise AttributeError('Not implemented yet!')

    def sort(self, *, key=..., reverse=...):
        raise AttributeError('Not implemented yet!')

    def __delitem__(self, key):
        self._notify_remove(key, self[key])
        super().__delitem__(key)

    def __iadd__(self, other):
        self.extend(other)

    def __imul__(self, n):
        length = len(self)
        super().__imul__(n)
        self._notify_add(slice(length, len(self)), self[length:len(self)])

    def __setitem__(self, key, value):
        self._notify_remove(key, self[key])
        super().__setitem__(key, value)
        self._notify_add(key, value)


class Renderer:
    __slots__ = ()

    def _render(self, string: ContentType):
        if isinstance(string, str):
            return string

        if callable(string):  # TODO: check this
            string = string()
        if isinstance(string, Tag):
            string = string._render(string.content)
        if isinstance(string, Iterable):
            string = ''.join(self._render(child) for child in string)

        # TODO: add html escaping
        return str(string)

    def __render__(self, *a, **kw):
        # leave here any arguments to haven't problems when override this method
        raise NotImplementedError


class Mounter:
    __slots__ = ()

    def __mount__(self, element: Union[Mounter, js.HTMLElement], index: Optional[int] = None):
        raise NotImplementedError


class _ChildrenList(Renderer, Mounter, TrackableList):
    __slots__ = ('parent', 'parent_index', 'ref', 'mounted')

    parent: Optional[Tag]
    parent_index: Optional[int]
    ref: Optional[Children]
    mounted: bool

    def __init__(self, iterable):
        super().__init__(iterable)
        self.parent = None
        self.parent_index = None
        self.ref = None
        self.mounted = False

    def copy(self) -> _ChildrenList:
        return _ChildrenList(super().copy())

    def __set_parent__(self, parent: Tag, index: int, ref: Children):
        self.parent = parent
        self.parent_index = index
        self.ref = ref

    def onchange(self):
        if self.ref and self.ref.onchange_trigger:
            self.ref.onchange_trigger(self.parent)

    def _notify_add_one(self, key: int, child: Tag):
        if not self.mounted:
            return

        child.__mount__(self.parent.children_element, key + self.parent_index)
        child.__render__()

    def _notify_remove_one(self, key: int, child: Tag):
        if not self.mounted:
            return

        try:
            self.parent.children_element.removeChild(child.mount_element)
        except Exception as e:
            if not str(e).startswith('NotFoundError'):
                raise

    def __render__(self):
        for child in self:
            child.__render__()

    def __mount__(self, element: js.HTMLElement, index=None):
        self.mounted = True

        if index is not None:
            index += self.parent_index
        for child in self:
            child.__mount__(element, index)


class ContentWrapper(Renderer, Mounter):
    __slots__ = ('content', 'tag', 'mount_element', 'parent', 'mount_parent', 'children', 'is_shadow')

    SHADOW_ROOTS = (
        'article', 'aside', 'blockquote', 'body', 'div', 'footer', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header',
        'main', 'nav', 'p', 'section', 'span',
    )

    content: Any
    tag: Optional[Tag]
    mount_element: Optional[js.HTMLElement]
    parent: Optional[Tag]
    mount_parent: Optional[js.HTMLElement]
    children: Optional[list[Tag, ...]]
    is_shadow: bool

    def __init__(self, content, tag):
        self.content = content
        self.tag = tag
        if tag:
            self.mount_element = tag.mount_element
            self.mount_element._py = self
        else:
            self.mount_element = None

        self.parent = None
        self.mount_parent = None
        self.children = None
        self.is_shadow = False

    def __mount__(self, element, index=None):
        self.parent = element._py
        self.mount_parent = element
        parent_name = element.tagName.lower()
        if self.tag:
            self.mount_element = self.tag.clone().mount_element
            self.mount_parent.insertChild(self.mount_element, index)
        elif '-' in parent_name or parent_name in self.SHADOW_ROOTS:
            self.is_shadow = True
            if self.mount_parent.shadowRoot:
                self.mount_parent = self.mount_parent.shadowRoot
            else:
                self.mount_element = self.mount_parent.attachShadow(mode='open')
            self.mount_element._py = self
        else:
            self.mount_element = js.document.createDocumentFragment()
            self.mount_element._py = self

    def __render__(self):
        _current['render'].append(self)
        _current['rerender'].append(self)
        log.debug('[__RENDER__]', _current)

        log.debug('[DEPENDENT]', _current['render'])
        if current_renderers := _current['render']:
            for renderer in current_renderers:
                if self.parent and renderer not in self.parent._dependents:
                    self.parent._dependents.append(renderer)

        if self.children:
            for child in self.children:
                child.__render__()

            log.debug('[END __RENDER__]', _current)
            if _current['render'][-1] is self:
                _current['render'].pop()
            return

        result: Union[ContentType, Tag] = self.content()

        result = self._render(result)
        if not isinstance(result, str):
            raise TypeError(f'Function {self.content} cannot return {result}!')

        if self.tag or self.is_shadow:
            self.mount_element.innerHTML = result
        else:  # fragment can't be re-rendered
            current_html = self.mount_parent.innerHTML
            if current_html != result and result:
                if current_html and not self.mount_parent._py._raw_html:
                    log.warn(
                        f'This html `{current_html}` will be replaces with this: `{result}`.\n'
                        'Maybe you must use pyweb.Tag instead of pyweb.tags.div',
                    )
                self.mount_parent.innerHTML = result

        log.debug('[END __RENDER__]', _current)
        if _current['render'][-1] is self:
            _current['render'].pop()

    def __repr__(self):
        return f'<[{self.parent} -> {self.content.__name__}]>'


class ChildRef(Renderer, Mounter):
    __slots__ = ('name', 'private_name', 'child')

    name: Optional[str]
    private_name: Optional[str]
    child: Tag

    def __init__(self, child: Optional[Tag]):
        self.name = None
        self.private_name = None
        self.child = child

    def __repr__(self):
        return f'{type(self).__name__}({self.child})'

    def __get__(self, instance: Optional[Tag], owner=None) -> Union[ChildRef, Tag]:
        if instance is None:
            return self

        return getattr(instance, self.private_name)

    def __set__(self, instance: Union[Tag, Type[Tag]], value):
        setattr(instance, self.private_name, value)

    def __delete__(self, instance: Tag):
        delattr(instance, self.private_name)

    def __set_name__(self, owner: Type[Tag], name: str):
        self.name = name
        self.private_name = '__child_' + name
        owner._static_children = owner._static_children.copy() + [self]
        self.__set__(owner, self.child)

    def _update_child(self, parent: Tag, index: int):
        clone = self.__get__(parent).clone()
        clone.__set_ref__(self)
        setattr(parent, self.name, clone)

    def __render__(self, parent: Tag):
        self.__get__(parent).__render__()

    def __mount__(self, element: Tag, index=None):
        self.__get__(element).__mount__(element.mount_element, index)


class Children(ChildRef):
    __slots__ = ('onchange_trigger',)

    child: _ChildrenList
    onchange_trigger: Optional[Callable]

    def __init__(self, child: list = ()):
        super().__init__(None)
        self.child = _ChildrenList(child)
        self.onchange_trigger = None

    def _update_child(self, parent: Tag, index: int):
        copy = self.__get__(parent).copy()
        copy.__set_parent__(parent, index, self)
        setattr(parent, self.name, copy)

    def __get__(self, instance: Optional[Tag], owner=None) -> Union[ChildRef, _ChildrenList]:
        return super().__get__(instance, owner)

    def __set__(self, instance, value):
        if isinstance(value, _ChildrenList):
            super().__set__(instance, value)
        else:
            current_value = self.__get__(instance)
            current_value[:] = value

    def __mount__(self, tag: Tag, index=None):
        self.__get__(tag).__mount__(tag.children_element, index)

    def onchange(self, handler):
        self.onchange_trigger = handler
        return handler


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
                    namespace[attribute_name] = child.as_child_ref()

        try:
            cls: Union[Type[Tag], type] = super().__new__(mcs, _name, bases, namespace)
        except Exception as e:
            log.error(traceback.format_exc())
            log.debug(e.__cause__, e)
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
            elif isinstance(content, Iterable) and content:
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
                    listener._add_listener(self.mount_element, event, self)
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
            pass  # TODO: for future


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


class on:
    __slots__ = ('_proxies', 'name', 'callback', 'get_parent')

    _proxies: list[pyodide.JsProxy]
    name: Optional[str]
    callback: Callable[[Tag, ...], Any]
    get_parent: bool

    def __init__(self, method):
        self._proxies = []
        self.get_parent = False

        if isinstance(method, str):
            self.name = method
            return

        self.name = None
        self(method)

    def __call__(self, method, get_parent=None):
        self.callback = method
        self.get_parent = get_parent
        return self

    def __get__(self, instance, owner=None):
        log.debug('[ON]', self, instance, owner)
        if instance is None:
            return self
        return self.callback

    def _call(self, tag, *args, **kwargs):
        if self.get_parent:
            tag = tag.parent
        if isinstance(self.callback, MethodType):
            fn = self.callback
        else:
            fn = MethodType(self.callback, tag)

        data = fn(*args, **kwargs)

        event, *_ = args

        _current['rerender'] = []
        for dependent in tag._dependents:
            if dependent in _current['rerender']:
                continue
            # TODO: move to other place
            log.debug('[_CALL]', 1, fn, dependent)
            dependent.__render__()
        _current['rerender'] = []

        if hasattr(event.currentTarget, '_py'):
            log.debug('[_CALL]', 2, event.currentTarget._py)
            event.currentTarget._py.__render__()
        else:
            log.debug('[_CALL]', 3, fn)
            tag.__render__()

        return data

    def _add_listener(self, element: js.HTMLElement, event_name, tag):
        orig_method = partial(self._call, tag)

        @js_func()
        def method(event):
            try:
                return orig_method(event)
            except Exception as error:
                log.debug(self, element, event_name, tag)  # make available args for debugging
                _debugger(error)

        method._locals = locals().copy()

        self._proxies.append(method)
        element.addEventListener(event_name, method)

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self.name} event handler')

    def __delete__(self, instance):
        pass

    def __del__(self):
        if not pyodide.IN_BROWSER:
            return
        for proxy in self._proxies:
            proxy.destroy()

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

        owner.listeners[self.name].append(self)
        log.debug('[__SET_NAME__]', self, owner)

    def __repr__(self):
        return f'on_{self.name}({self.callback})'


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


__all__ = [
    '__version__', '__CONFIG__', 'delay', '_debugger', 'AttrType', 'ContentType', 'log', 'AttrValue', 'attr', 'state',
    'html_attr', 'html_state', 'Trackable', 'TrackableList', 'Renderer', 'Mounter', 'ContentWrapper', 'ChildRef',
    'Children', '_MetaTag', 'Tag', 'on', 'empty_tag', 'mount',
]
