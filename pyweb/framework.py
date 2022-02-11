from __future__ import annotations as _

import traceback
from collections import defaultdict
from typing import Union, Callable, Any, Type, Iterable, Optional
from types import MethodType
from functools import wraps, partial
import inspect

import js
import pyodide

# [PYWEB IGNORE START]
from .utils import to_kebab_case
# [PYWEB IGNORE END]


if not pyodide.IN_BROWSER:
    js.Element.__str__ = lambda self: f'<{self.tagName.lower()}>'


def _debugger():
    js.console.log(pyodide.to_js(inspect.currentframe().f_back.f_locals))
    js.console.warn('\n'.join(traceback.format_stack()[5:]))
    js._DEBUGGER()


AttrType = Union[None, str, int, bool, Iterable['AttrType'], dict[str, 'AttrType'], 'Tag']
ContentType = Union[str, Iterable, 'Renderer']


_current_render: list[Renderer, ...] = []
_current__lifecycle_method: dict[str, dict[int, Tag]] = {}
_current: Any = {
    'render': _current_render,
    '_lifecycle_method': _current__lifecycle_method,
}


class AttrValue:
    """
    Extend this class to be able to use it as value in pyweb.attr and children
    """

    def __view_value__(self):
        """ This method will be called on render, must return serializable value """


MISSING = object()


class attr:
    _view = True

    __slots__ = ('name', 'private_name', 'value', 'factory', 'type')

    name: Optional[str]
    private_name: Optional[str]
    value: Any
    factory: Callable
    type: Optional[Type]

    def __init__(self, value=None, *, default_factory=None):
        self.name = None
        self.private_name = None
        self.value = value
        self.factory = default_factory

        self.type = type(None)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        print('pre [__GET__]', instance, instance.__dict__)

        value = getattr(instance, self.private_name, MISSING)

        print(
            '[__GET__]',
            value,
            self.name,
            (instance, owner, self),
            instance.mount_parent._py if hasattr(instance, 'mount_parent') else '----',
            sep='\n! ',
        )

        if value is MISSING:
            return

        return value

    def __set__(self, instance, value):
        print('[__SET__]', instance, self.name, value)
        if self.factory is not None:
            value = self.factory(value)
        setattr(instance, self.private_name, value)

    def __set_name__(self, owner, name):
        self.name = to_kebab_case(name)
        self.private_name = '_' + name
        if self.value is not None:
            self.__set__(owner, self.value)

    def __set_type__(self, type):
        self.type = type

    def __delete__(self, instance):
        return delattr(instance, self.private_name)

    def __repr__(self):
        return f'{self.name}({self.value!r})'

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


class const_attr(attr):
    __slots__ = ()

    def __set__(self, instance, value):
        if getattr(instance, self.private_name, None) is not None:
            raise AttributeError
        super().__set__(instance, value)


class const_state(const_attr, state):
    __slots__ = ()


class Renderer:
    __slots__ = ()

    def _render(self, string: ContentType):
        if isinstance(string, str):
            return string

        if callable(string):
            string = string()
        if isinstance(string, Tag):
            string = string._render(string.content)
        if isinstance(string, Iterable):
            string = ''.join(self._render(child) for child in string)

        # TODO: add html escaping
        return str(string)

    def __render__(self, *a, **kw):
        # leave here any arguments to haven't problems when override this method
        raise NotImplemented


class Mounter:
    __slots__ = ()

    def __mount__(self, element: Union[Mounter, js.HTMLElement]):
        raise NotImplemented


class ChildWrapper(Renderer, Mounter):
    __slots__ = ('child', 'tag', 'mount_element', 'parent', 'mount_parent')

    child: Any
    tag: Optional[str]
    mount_element: js.HTMLElement
    parent: Optional[js.HTMLElement]
    mount_parent: Optional[js.HTMLElement]

    def __init__(self, child, tag):
        self.child = child
        self.tag = tag
        if tag:
            self.mount_element = js.document.createElement(tag)
        else:
            self.mount_element = js.document.createDocumentFragment()
        self.mount_element._py = self
        self.parent: None = None
        self.mount_parent: None = None

    def __mount__(self, element):
        self.parent = element._py
        self.mount_parent = element
        self.mount_parent.appendChild(self.mount_element)

    def __render__(self):
        _current['render'].append(self)
        print('[__RENDER__]', _current)

        print('[DEPENDENT]', _current['render'])
        if current_renderers := _current['render']:
            for renderer in current_renderers:
                if self.parent and renderer not in self.parent._dependents:
                    self.parent._dependents.append(renderer)

        result = self._render(self.child())
        if self.tag:
            self.mount_element.innerHTML = result
        else:  # fragment can't be re-rendered
            current_html = self.mount_parent.innerHTML
            if current_html != result:
                if current_html:
                    js.console.warn(
                        f'This html `{current_html}` will be replaces with this: `{result}`.'
                        'Maybe you must use pyweb.Tag instead of pyweb.tags.div',
                    )
                self.mount_parent.innerHTML = result

        print('[END __RENDER__]', _current)
        if _current['render'][-1] is self:
            _current['render'].pop()

    def __repr__(self):
        return f'<[{self.parent} -> {self.child.__name__}]>'


class ChildRef(Renderer, Mounter):
    __slots__ = ('name', 'private_name', 'child')

    name: Optional[str]
    private_name: Optional[str]
    child: Tag

    def __init__(self, child: Tag):
        self.name = None
        self.private_name = None
        self.child = child

    def __repr__(self):
        return f'{type(self).__name__}({self.child})'

    def __get__(self, instance: Optional[Tag], owner=None) -> Tag:
        if instance is None:
            return self

        return getattr(instance, self.private_name)

    def __set__(self, instance: Union[Tag, Type[Tag]], value):
        setattr(instance, self.private_name, value)

    def __delete__(self, instance: Tag):
        delattr(instance, self.private_name)

    def __set_name__(self, owner: Union[Tag, Type[Tag]], name: str):
        self.name = name
        self.private_name = '_' + name
        owner._static_children = owner._static_children.copy() + [self]
        self.__set__(owner, self.child)

    def update_child(self, parent: Tag):
        setattr(parent, self.name, self.__get__(parent).clone())

    def __render__(self, parent: Tag):
        self.__get__(parent).__render__()

    def __mount__(self, element: Tag):
        self.__get__(element).__mount__(element.mount_element)


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
    def __new__(mcs, _name, bases, namespace, **kwargs):
        namespace = namespace.copy()
        print('[__NAMESPACE__]', namespace)

        initialized = _TAG_INITIALIZED  # if class Tag is already defined

        is_root = kwargs.get('_root')
        if is_root:
            tag_name = ''
            namespace['__ROOT__'] = True
        else:
            tag_name = kwargs.get('name')

        is_sub_tag = bool(tag_name)
        if tag_name:
            namespace['_tag_name_'] = to_kebab_case(tag_name)

        if 'content_tag' in kwargs:
            namespace['_content_tag'] = kwargs['content_tag']

        namespace['methods'] = defaultdict(list)

        super_children_index = -1
        super_children = namespace.get('children', [])
        if isinstance(super_children, property):
            super_children = None

        if super_children:
            namespace.pop('children', None)
            super_children = list(super_children)

        if super_children is not None:
            if '__SUPER__' not in super_children:
                super_children.insert(0, '__SUPER__')
            super_children_index = super_children.index('__SUPER__')

        attrs = {}

        if not is_root and (annotations := namespace.get('__annotations__')):
            for name, _type in annotations.items():
                if not (attribute := namespace.get(name)) or not isinstance(attribute, attr):
                    continue

                attribute.__set_type__(_type)
                attrs[name] = attribute

        if initialized:
            for attribute_name, child in tuple(namespace.items()):
                if isinstance(child, Tag):
                    namespace[attribute_name] = ChildRef(child)

        try:
            cls: Union[Type[Tag], type] = super().__new__(mcs, _name, bases, namespace)
        except Exception as e:
            js.console.error(traceback.format_exc())
            print(e.__cause__, e)
            raise e

        if not hasattr(cls, '_content_tag'):
            cls._content_tag = 'div'

        if initialized:
            cls.attrs.update(attrs)
        else:
            cls.attrs = attrs

        if not hasattr(cls, '_static_children'):
            cls._static_children = []

        if is_sub_tag or not isinstance(getattr(cls, 'children', None), property):
            if super_children:
                super_children = super_children.copy()
                super_children[super_children_index: super_children_index + 1] = cls._static_children
                cls._static_children = super_children
            else:
                cls._static_children = cls._static_children.copy()
        else:
            cls._static_children = ['__CONTENT__']

        cls._children = cls._static_children

        if is_sub_tag:
            cls._methods = cls._methods.copy()
            for _key, _value in cls.methods.items():
                cls._methods[_key].extend(_value)
        else:
            cls._methods = defaultdict(list)

        if '__mount__' in namespace:
            cls.__mount__ = mcs.__mount(cls.__mount__)

        if '__render__' in namespace:
            cls.__render__ = mcs.__render(cls.__render__)

        if '__init__' in namespace:
            cls.__init__ = mcs.__init(cls.__init__)

        return cls

    @_lifecycle_method
    def __mount(self: Tag, args, kwargs, _original_func, _not_in_super_call):
        print('[__MOUNT__]', self, args, kwargs, _original_func, _not_in_super_call, args[0]._py)

        element, = args
        if _not_in_super_call:
            self.parent = element._py
            self.mount_parent = element
            self.mount_parent.appendChild(self.mount_element)
            for child in self.children:
                if isinstance(child, ChildRef):
                    child.__mount__(self)
                elif isinstance(child, Mounter):
                    child.__mount__(self.mount_element)
                else:
                    js.console.warn(child)

        result = _original_func(self, *args, **kwargs)

        if _not_in_super_call:
            self.mount()

        return result

    @_lifecycle_method
    def __render(self: Tag, args, kwargs, _original_func, _not_in_super_call):
        _current['render'].append(self)

        result = _original_func(self, *args, **kwargs)

        if _current['render'][-1] is self:
            _current['render'].pop()

        if _not_in_super_call:
            self.render()

        return result

    @_lifecycle_method
    def __init(self: Tag, args, kwargs, _original_func, _not_in_super_call):
        children_argument = None

        if _not_in_super_call:
            children_argument = kwargs.get('children')
            if children_argument and not isinstance(children_argument, Iterable):
                children_argument = (children_argument,)
            self._kwargs = kwargs
            self._dependents = []
            self.mount_element = js.document.createElement(self._tag_name_)
            self.mount_element._py = self
            self.children = self.children.copy()

        _original_func(self, *args, **kwargs)

        if _not_in_super_call:
            if children_argument:
                self._children += self._handle_children(children_argument)

            for event, methods in self._methods.items():
                for method in methods:
                    method._add_listener(self.mount_element, event, self)


class Child(property):
    def __set_name__(self, owner: Tag, name: str):
        owner._static_children = owner._static_children.copy() + [ChildWrapper(self.fget, self.fget.__name__)]


class Tag(Renderer, Mounter, metaclass=_MetaTag, _root=True):
    _dependents: list[Tag, ...]
    _kwargs: dict[str, AttrType]

    _tag_name_: str
    attrs: dict[str, attr]
    methods: defaultdict[str, list[on, ...]]
    _methods: defaultdict[str, list[on, ...]]
    mount_element: js.HTMLElement
    mount_parent: js.HTMLElement
    parent: Optional[Tag]
    content: Union[ContentType, Callable[[Tag], ContentType]]
    _static_children: list[ContentType, ...]
    _children: list[Mounter, ...]

    def __init__(self, **kwargs: AttrType):
        for key, _attr in self.attrs.items():
            if key not in kwargs:
                continue

            value = kwargs[key]

            # TODO: check this
            if callable(value):
                value = partial(value, self)
            setattr(self, key, value)

    def __repr__(self):
        return f'{type(self).__name__}(<{self._tag_name_}/>)'

    def __html__(self, children=None) -> str:
        if children:
            return f'<{self._tag_name_} {self.__attrs__}>{self._render(children)}</{self._tag_name_}>'
        return f'<{self._tag_name_} {self.__attrs__} />'

    @classmethod
    def comment(cls, string) -> str:
        return f'<!-- {string} -->'

    @property
    def __attrs__(self) -> dict[str, AttrType]:
        return {
            _attr.name: value
            for _attr in self.attrs.values()
            if _attr._view and (value := _attr.__get_view_value__(self)) is not None
        }

    @property
    def __states__(self) -> dict[str, AttrType]:
        return {
            _attr.name: _attr.__get__(self)
            for _attr in self.attrs.values()
        }

    def __render__(
        self, attrs: Optional[dict[str, AttrType]] = None, children: Optional[Iterable[ContentType]] = None
    ):
        for name, value in (attrs or self.__attrs__).items():
            self.mount_element.setAttribute(name, value)

        print(children, self.children)
        for child in (children or self.children):
            if isinstance(child, ChildRef):
                child.__render__(self)
            elif isinstance(child, Renderer):
                child.__render__()
            else:  # string ?
                self.mount_element.append(self._render(child))

    def render(self):
        """empty method for easy override with code for run after render"""

    def content(self) -> str:
        return ''

    def __mount__(self, element):
        pass  # see _MetaTag.__mount

    def mount(self):
        """empty method for easy override with code for run after mount"""

    @property
    def children(self) -> list[Mounter, ...]:
        return self._children

    @children.setter
    def children(self, children):
        self._children = self._handle_children(children)

    def _handle_children(self, children):
        result = []

        for child in children:
            result.append(child)

            if isinstance(child, ChildWrapper):
                child = child.child.__func__

            if child == '__CONTENT__':
                child = self.content
                if not callable(child):
                    child = MethodType(lambda s: s.content, self)

            if isinstance(child, ChildRef) and child in self._children:
                # special case for wrapped Tag - generated when using Tag as descriptor
                # this allows save reference from parent to new copy of child
                child.update_child(self)
            elif isinstance(child, Tag):
                result[-1] = child = child.clone()
            elif callable(child):
                if not isinstance(child, MethodType):
                    child = MethodType(child, self)
                result[-1] = child = ChildWrapper(child, self._content_tag)
            elif isinstance(child, str):
                continue

        return result

    # descriptor part
    def __get__(self, instance, owner):
        return self

    def clone(self) -> Tag:
        clone = type(self)(**self._kwargs)
        clone.children = self.children
        return clone


_TAG_INITIALIZED = True


class on:
    __slots__ = ('_proxies', 'method_name', 'name', 'callback')

    _proxies: list[pyodide.JsProxy]
    method_name: Optional[str]
    name: Optional[str]
    callback: Callable[[Tag, ...], Any]

    def __init__(self, method):
        self._proxies = []
        self.method_name = None

        if isinstance(method, str):
            self.name = method
            return

        self.name = None
        self(method)

    def __call__(self, method):
        self.callback = method
        return self

    def __get__(self, instance, owner):
        print('[ON]', self, instance, owner)
        if instance is None:
            return self
        return partial(self._call, instance)

    def _call(self, tag, *args, **kwargs):
        if isinstance(self.callback, MethodType):
            fn = self.callback
        else:
            fn = MethodType(self.callback, tag)

        data = fn(*args, **kwargs)

        for dependent in tag._dependents:
            # TODO: move to other place
            # TODO: check for children to prevent extra re-renders
            print('[_CALL]', 1, fn, dependent)
            dependent.__render__()

        if isinstance(fn.__self__, Tag):
            print('[_CALL]', 2, fn)
            fn.__self__.__render__()
        else:
            print('[_CALL]', 3, fn)
            tag.__render__()

        return data

    def _add_listener(self, element: js.HTMLElement, event_name, tag):
        method = getattr(tag, self.method_name)
        proxy = pyodide.create_proxy(method)
        self._proxies.append(proxy)
        element.addEventListener(event_name, proxy)

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self.name} event handler')

    def __delete__(self, instance):
        pass

    def __del__(self):
        for proxy in self._proxies:
            proxy.destroy()

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

        self.method_name = name

        owner.methods[self.name].append(self)
        print('[__SET_NAME__]', self, owner)

    def __repr__(self):
        return f'on_{self.name}({self.callback})'


def mount(element: Tag, root_element: str):
    parent = js.document.querySelector(root_element)
    if parent is None:
        raise NameError('Mount point not found')
    parent._py = None
    element.__mount__(parent)
    element.__render__()
