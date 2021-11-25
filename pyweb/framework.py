from collections import defaultdict
from typing import Union, Callable, Any, Type, Iterable, Optional
from types import MethodType
from functools import wraps, partial

import js

# [PYWEB IGNORE START]
from .utils import to_kebab_case
# [PYWEB IGNORE END]


AttrType = Union[None, str, int, bool, list['AttrType', ...], dict[str, 'AttrType'], 'Tag']
ContentType = Union[str, Iterable, 'Renderer']


_current_render: list['Renderer', ...] = []
_current__lifecycle_method: dict[str, dict[str, 'Tag']] = {}
_current = {
    'render': _current_render,
    '_lifecycle_method': _current__lifecycle_method,
}


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

        value = getattr(instance, self.private_name)

        print(
            '[__GET__]',
            value,
            self.name,
            (instance, owner, self),
            instance.mount_parent._py if hasattr(instance, 'mount_parent') else '----',
            sep='\n! ',
        )

        return value

    def __set__(self, instance, value):
        print('[__SET__]', instance, value)
        if self.factory is not None:
            value = self.factory(value)
        setattr(instance, self.private_name, value)

    def __set_name__(self, owner, name):
        self.name = to_kebab_case(name)
        self.private_name = '_' + name
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
        if hasattr(self.type, '__view_value__'):
            return value.__view_value__()

        return value


class state(attr):
    __slots__ = ()

    _view = False


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

    def __render__(self):
        raise NotImplemented


class ChildWrapper(Renderer):
    __slots__ = ('child', 'tag', 'element', 'parent')

    child: Any
    tag: Optional[str]
    element: js.HTMLElement
    parent: js.HTMLElement  # Optional[js.HTMLElement]  # raises error due to JsProxy is not hashable

    def __init__(self, child, tag):
        self.child = child
        self.tag = tag
        if tag:
            self.element = js.document.createElement(tag)
        else:
            self.element = js.document.createDocumentFragment()
        self.element._py = self
        self.parent: None = None

    def __mount__(self, element):
        self.parent = element
        self.parent.appendChild(self.element)

    def __render__(self):
        _current['render'].append(self)
        print('[__RENDER__]', _current)

        print('[DEPENDENT]', _current['render'])
        if current_renderers := _current['render']:
            for renderer in current_renderers:
                if self.parent._py and renderer not in self.parent._py._dependents:
                    self.parent._py._dependents.append(renderer)

        result = self._render(self.child())
        if self.tag:
            self.element.innerHTML = result
        else:  # fragment can't be re-rendered
            self.parent.innerHTML = result

        print('[END __RENDER__]', _current)
        if _current['render'][-1] is self:
            _current['render'].pop()

    def __repr__(self):
        return f'<<{self.parent._py} -> {self.child.__name__}>>'


def _lifecycle_method(fn):
    name = fn.__name__
    attr_name = f'_wrapper_{name}_calling'
    _cache = _current['_lifecycle_method'][attr_name] = {}

    @wraps(fn)
    def lifecycle_method(original_func, *a, **kw):
        @wraps(original_func)
        def original_method(self, *args, **kwargs):
            # prevent calling super() calls extra code twice
            not_in_super_call = str(self) not in _cache

            if not_in_super_call:
                _cache[str(self)] = self

            result = fn(
                self, args, kwargs, *a, **kw, _original_func=original_func, _not_in_super_call=not_in_super_call
            )

            if not_in_super_call:
                del _cache[str(self)]

            return result
        return original_method
    return lifecycle_method


class _MetaTag(type):
    def __new__(mcs, _name, bases, namespace, **kwargs):
        print('[__NAMESPACE__]', namespace)
        is_sub_tag = any(getattr(base, '_name', '') for base in bases)

        is_root = kwargs.get('_root')
        if is_root:
            tag_name = ''
            namespace['__ROOT__'] = True
        else:
            tag_name = kwargs.get('name')

        if tag_name:
            namespace['_name'] = to_kebab_case(tag_name)

        if 'content_tag' in kwargs:
            namespace['_content_tag'] = kwargs['content_tag']

        super_children = namespace.pop('children', None)
        super_children_index = -1

        if super_children:
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

        try:
            cls: Union[Type[Tag], type] = super().__new__(mcs, _name, bases, namespace)
        except Exception as e:
            print(e.__cause__, e)
            raise e

        if not hasattr(cls, '_content_tag'):
            cls._content_tag = 'div'

        if is_sub_tag:
            cls.attrs.update(attrs)
        else:
            cls.attrs = attrs

        if is_sub_tag or getattr(cls, 'children', None):
            if super_children:
                super_children = super_children.copy()
                super_children[super_children_index: super_children_index + 1] = cls.children
                cls.children = super_children
            else:
                cls.children = cls.children.copy()
        else:
            cls.children = ['__CONTENT__']

        print('[METHODS]', cls, is_sub_tag, getattr(cls, 'methods', None))
        if is_sub_tag or hasattr(cls, 'methods'):
            cls.methods = cls.methods.copy()
        else:
            cls.methods = defaultdict(list)

        if '__mount__' in namespace:
            cls.__mount__ = mcs.__mount(cls.__mount__)

        if '__render__' in namespace:
            cls.__render__ = mcs.__render(cls.__render__)

        if '__init__' in namespace:
            cls.__init__ = mcs.__init(cls.__init__, content_tag=cls._content_tag)

        return cls

    @_lifecycle_method
    def __mount(self: 'Tag', args, kwargs, _original_func, _not_in_super_call):
        print('[__MOUNT__]', self, args, kwargs, _original_func, _not_in_super_call)

        element, = args
        if _not_in_super_call:
            self.mount_parent = element
            self.mount_parent.appendChild(self.mount_element)

        return _original_func(self, *args, **kwargs)

    @_lifecycle_method
    def __render(self: 'Tag', args, kwargs, _original_func, _not_in_super_call):
        return _original_func(self, *args, **kwargs)

    @_lifecycle_method
    def __init(self: 'Tag', args, kwargs, _original_func, _not_in_super_call, content_tag):
        if _not_in_super_call:
            self._kwargs = kwargs
            self._dependents = []
            self.mount_element = js.document.createElement(self._name)
            self.mount_element._py = self

        _original_func(self, *args, **kwargs)

        if _not_in_super_call:
            print('[__CHILDREN__]', self, self.children)
            for index, child in enumerate(self.children):
                if child == '__CONTENT__':
                    child = self.content
                    if not callable(child):
                        child = MethodType(lambda s: child, self)
                    # TODO: line below fixes when tag is used several times, '__CONTENT__' does not work properly
                    self.children = self.children.copy()
                if isinstance(child, Tag):
                    self.children[index] = child = child.clone()
                elif callable(child):
                    self.children[index] = child = ChildWrapper(child, content_tag)

                child.__mount__(self.mount_element)
            print('[__CHILDREN__]', self, self.children)

            print('[M]', self, self.methods)
            for event, methods in self.methods.items():
                print(event, methods)
                for method in methods:
                    self.mount_element.addEventListener(event, getattr(self, method.method_name))


class Child(property):
    def __set_name__(self, owner: 'Tag', name: str):
        owner.children.append(ChildWrapper(self.fget, self.fget.__name__))


class Tag(Renderer, metaclass=_MetaTag, _root=True):
    _dependents: list['Tag', ...]
    _kwargs: dict[str, AttrType]

    _name: str
    attrs: dict[str, attr]
    methods: defaultdict[str, list['on', ...]]
    mount_element: js.HTMLElement
    mount_parent: js.HTMLElement
    content: Union[ContentType, Callable[['Tag'], ContentType]]
    children: list[ContentType, ...] = []

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
        return f'{type(self).__name__}(<{self._name}/>)'

    @property
    def parent(self) -> Optional['Tag']:
        return self.mount_parent._py

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

    def __render__(self):
        _current['render'].append(self)
        print('[__RENDER__]', _current, self)

        for name, value in self.__attrs__.items():
            self.mount_element.setAttribute(name, value)

        print(self.children)
        for child in self.children:
            if isinstance(child, Renderer):
                child.__render__()
            else:  # string ?
                self.mount_element.append(self._render(child))

        print('[END __RENDER__]', _current)
        if _current['render'][-1] is self:
            _current['render'].pop()

    def content(self) -> str:
        return ''

    def __mount__(self, element):
        pass  # see _MetaTag.__mount

    # descriptor part
    def __get__(self, instance, owner):
        return self

    def __set_name__(self, owner: 'Tag', name: str):
        owner.children.append(self)

    def clone(self) -> 'Tag':
        clone = type(self)(**self._kwargs)
        return clone


class on:
    __slots__ = ('method_name', 'name', 'callback')

    method_name: Optional[str]
    name: Optional[str]
    callback: Callable[['Tag', ...], Any]

    def __init__(self, method):
        self.method_name = None

        if isinstance(method, str):
            self.name = method
            return

        self.name = None
        self.callback = method

    def __call__(self, method):
        self.callback = method
        return self

    def __get__(self, instance, owner):
        print('[ON]', self, instance, owner)
        if instance is None:
            return self
        return partial(self._call, instance)

    def _call(self, tag, *args, **kwargs):
        fn = self.callback

        data = fn(tag, *args, **kwargs)

        for dependent in tag._dependents:
            print('[_CALL]', 1, fn, dependent)
            dependent.__render__()

        if isinstance(fn, MethodType) and isinstance(fn.__self__, Tag):
            print('[_CALL]', 2, fn)
            fn.__self__.__render__()
        else:
            print('[_CALL]', 3, fn)
            tag.__render__()

        return data

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self.name} event handler')

    def __delete__(self, instance):
        pass

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
    parent._py = None
    element.__mount__(parent)
    element.__render__()
