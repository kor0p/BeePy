from collections import defaultdict
from typing import Union, Callable, Any, Type, Iterable, Optional
from types import FunctionType, MethodType
from functools import wraps, partial

import js


AttrType = Union[None, str, int, bool, list['AttrType', ...], dict[str, 'AttrType'], 'Tag']
ContentType = Union[str, Iterable, 'Renderer']


_current: dict[str, list['Renderer', ...]] = {
    'render': [],
}


class attr:
    __slots__ = ('_value', )

    _view = True

    def __init__(self, value=None):
        self._value = value


class state(attr):
    _view = False


class Attribute:
    __slots__ = ('name', 'private_name', 'value', 'base')

    name: str
    private_name: str
    value: Any
    base: attr

    def __init__(self, name, type, value, base):
        self.name = name
        self.private_name = '_' + name
        self.value = value
        self.base = base

    def __get__(self, instance, owner, *, raw=False):
        if instance is None:
            return self
        value = getattr(instance, self.private_name)

        print(
            '[__GET__]',
            raw,
            value,
            instance,
            owner,
            self,
            instance.mount_parent._py if hasattr(instance, 'mount_parent') else '----',
            sep='!\t\t!',
        )
        if not raw:
            if instance._rendering:
                instance.attrs.pop(self.name, None)

        return value

    def __set__(self, instance, value):
        setattr(instance, self.private_name, value)

        if not isinstance(instance, Tag):
            return

        print('[__SET__]', instance, instance._dependents, value)
        for dependent in instance._dependents:
            dependent.__render__()
        else:
            instance.__render__()

    def __delete__(self, instance):
        return delattr(instance, self.private_name)

    def __str__(self):
        return f'{self.name}({self.value})'


class Renderer:
    def _render(self, string: ContentType):
        if isinstance(string, str):
            return string

        if isinstance(string, (MethodType, FunctionType)):
            string = string()
        if isinstance(string, Tag):
            string = string._render(string.content)
        if isinstance(string, Iterable):
            string = ''.join(self._render(child) for child in string)

        # TODO: add html escaping
        return str(string)

    def __render__(self):
        raise NotImplemented


class MethodChildWrapper(Renderer):
    def __init__(self, method, raw=False):
        self.method = method
        self.raw = raw
        if raw:
            self.element = js.document.createDocumentFragment()
        else:
            self.element = js.document.createElement('div')
        self.element._py = self

    def __mount__(self, element):
        self.parent = element
        self.parent.appendChild(self.element)

    def __render__(self):
        _current['render'].append(self)
        print('[__RENDER__]', _current)

        print('[DEPENDENT]', _current['render'])
        if current_renderers := _current['render']:
            for renderer in current_renderers:
                if renderer not in self.method.__self__._dependents:
                    self.method.__self__._dependents.append(renderer)

        result = self._render(self.method())
        if self.raw:  # fragment can't be re-rendered
            self.parent.innerHTML = result
        else:
            self.element.innerHTML = result

        print('[END __RENDER__]', _current)
        if _current['render'][-1] is self:
            _current['render'].pop()

    def __str__(self):
        return f'{type(self)}[{self.method}]'


class _MetaTag(type):
    def __new__(mcs, _name, bases, namespace, **kwargs):
        is_sub_tag = any(getattr(base, '_name', '') for base in bases)

        is_root = kwargs.pop('_root', False)
        if is_root:
            tag_name = '__ROOT__'
            namespace['__ROOT__'] = True
        else:
            tag_name = kwargs.get('name')

        if tag_name:
            namespace['_name'] = tag_name

        raw_content = kwargs.get('raw_content')

        attrs = {}

        if not is_root and (annotations := namespace.get('__annotations__')):
            for name, _type in annotations.items():
                if not (_attr := namespace.get(name)) or not isinstance(_attr, attr):
                    continue

                value = _attr._value
                attrs[name] = value
                namespace[name] = Attribute(name, _type, value, _attr)

        namespace['attrs'] = attrs

        try:
            cls: Type[Tag] = super().__new__(mcs, _name, bases, namespace)
        except Exception as e:
            print(e.__cause__, e)
            raise e

        if is_sub_tag:
            cls.attrs.update(attrs)
        else:
            cls.attrs = attrs

        if is_sub_tag:
            cls.children = cls.children.copy()
        else:
            cls.children = ['__CONTENT__']

        print('[METHODS]', cls, is_sub_tag, getattr(cls, 'methods', None))
        if is_sub_tag or hasattr(cls, 'methods'):
            cls.methods = cls.methods.copy()
        else:
            cls.methods = {}

        for key, value in attrs.items():
            getattr(cls, key).__set__(cls, value)

        if '__render__' in namespace:
            original_render_func = cls.__render__
            setattr(
                cls, '__render__', wraps(cls.__render__)(
                    lambda self, *a, **kw: mcs.__render_wrapper(self, original_render_func, a, kw)
                )
            )

        if '__init__' in namespace:
            original_init_func = cls.__init__
            setattr(
                cls, '__init__', wraps(cls.__init__)(
                    lambda self, *a, **kw: mcs.__init_wrapper(self, original_init_func, raw_content, a, kw)
                )
            )

        return cls

    def __render_wrapper(self: 'Tag', original_func, args, kwargs):
        # prevent super() call
        _hasnt_calling_attr = not hasattr(self, '_render_wrapper_calling')

        if _hasnt_calling_attr:
            self._render_wrapper_calling = True
            self._rendering, self.attrs = self.attrs, self.attrs.copy()

            for key in tuple(self.attrs.keys()):
                self.attrs[key] = getattr(type(self), key).__get__(self, type(self), raw=True)

        result = original_func(self, *args, **kwargs)

        if _hasnt_calling_attr:
            self._rendering, self.attrs = {}, self._rendering

            del self._render_wrapper_calling

        return result

    def __init_wrapper(self: 'Tag', original_func, raw_content, args, kwargs):
        # prevent super() call
        _hasnt_calling_attr = not hasattr(self, '_init_wrapper_calling')
        if _hasnt_calling_attr:
            self._init_wrapper_calling = True

            self._dependents = []
            self.mount_element = js.document.createElement(self._name)
            self.mount_element._py = self

        original_func(self, *args, **kwargs)

        if _hasnt_calling_attr:

            print('[__CHILDREN__]', self, self.children)
            for index, child in enumerate(self.children):
                if child == '__CONTENT__':
                    child = self.content
                    self.children = self.children.copy()
                if isinstance(child, (MethodType, FunctionType)):
                    self.children[index] = child = MethodChildWrapper(child, raw=raw_content)

                child.__mount__(self.mount_element)
            print('[__CHILDREN__]', self, self.children)

            print('[M]', self, self.methods)
            for event, methods in self.methods.items():
                print(event, methods)
                for method in methods:
                    self.mount_element.addEventListener(event, getattr(self, method.method_name))

            for key, value in kwargs.items():
                if key not in self.attrs:
                    continue
                if isinstance(value, FunctionType):
                    _fn = value

                    @wraps(_fn)
                    def value(*a, **kw):
                        return _fn(self, *a, **kw)
                setattr(self, key, value)

            del self._init_wrapper_calling


class Child(property):
    def __set_name__(self, owner: 'Tag', name: str):
        owner.children.append(MethodChildWrapper(self.fget))


class Tag(Renderer, metaclass=_MetaTag, _root=True):
    _rendering: dict[str, AttrType] = {}
    _dependents: list['Tag', ...] = []

    _name: str
    attrs: dict[str, AttrType]
    methods: defaultdict[str, list['on', ...]] = defaultdict(list)
    mount_element: Any  # js.HtmlTag
    mount_parent: Any
    content: Union[ContentType, Callable[['Tag'], ContentType]]
    children: list[ContentType, ...] = []

    def __init__(self, **kwargs):
        pass

    @property
    def parent(self):
        return self.mount_parent._py

    @classmethod
    def comment(cls, string):
        return f'<!-- {string} -->\n'

    def __attrs__(self):
        return {
            key: value for key, value in self.attrs.items()
            if getattr(type(self), key).base._view
        }

    def __render__(self):
        _current['render'].append(self)
        print('[__RENDER__]', _current)

        for name, value in self.__attrs__().items():
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

    def content(self):
        return ''

    def __mount__(self, element):
        self.mount_parent = element
        self.mount_parent.appendChild(self.mount_element)

    # descriptor part
    def __get__(self, instance, owner):
        return self

    def __set_name__(self, owner: 'Tag', name: str):
        owner.children.append(self)


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

        print('[_CALL]', fn, tag._dependents)
        if hasattr(fn, '__wrapped__'):
            fn = fn.__wrapped__

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

    def __str__(self):
        return f'on_{self.name}({self.callback})'


def mount(element: Tag, root_element: str):
    parent = js.document.querySelector(root_element)
    parent._py = None
    element.__mount__(parent)
    element.__render__()
