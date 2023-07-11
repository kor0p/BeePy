from __future__ import annotations

from abc import abstractmethod
from typing import Optional, Callable, Union, Type, TypeVar, Generic, Iterable

import beepy
from beepy.types import Tag, Renderer, WebBase, Children, ContentType
from beepy.context import Context
from beepy.utils import js, log
from beepy.utils.internal import _PY_TAG_ATTRIBUTE


class CustomWrapper(WebBase):
    pass


class StringWrapper(CustomWrapper):
    __slots__ = ('content',)

    def __init__(self, string):
        self.content = string

    def __mount__(self, element, parent: Tag, index=None):
        element.insertChild(self._render(self.content).format(self=parent), index)

    def __repr__(self):
        return f'String({self.content})'


class ContentWrapper(CustomWrapper):
    __slots__ = ('content', 'tag', 'mount_element', '_current_render', 'parent', 'mount_parent', 'children')

    SHADOW_ROOTS = (
        'article', 'aside', 'blockquote', 'body', 'div', 'footer', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header',
        'main', 'nav', 'p', 'section', 'span',
    )

    content: Callable[[], Union[ContentType, Tag]]
    tag: Optional[Tag]
    mount_element: Optional[js.HTMLElement]
    _current_render: list[Renderer]
    parent: Optional[Tag]
    mount_parent: Optional[js.HTMLElement]
    children: Optional[list[Tag]]

    def __init__(self, content, tag, _current_render):
        self.content = content
        self.tag = tag
        if tag:
            self.mount_element = tag.mount_element
        else:
            self.mount_element = None

        self._current_render = _current_render
        self.parent = None
        self.mount_parent = None
        self.children = None

    def __mount__(self, element, parent: Tag, index=None):
        self.parent = parent
        self.mount_parent = element
        parent_name = element.tagName.lower()
        if self.tag:
            self.mount_element = self.tag.clone(parent).mount_element
            self.mount_parent.insertChild(self.mount_element, index)
        elif ('-' in parent_name or parent_name in self.SHADOW_ROOTS) and False:
            # TODO: add some param to use shadow root directly
            # (or) TODO[fix]: with shadow root children cannot be rendered
            # (or) TODO: at least warn developer, or raise error, if not fixed
            if self.parent._shadow_root:
                self.mount_element = self.parent._shadow_root
            else:
                self.mount_element = self.mount_parent.attachShadow(mode='closed')
            self.parent._shadow_root = self.mount_element
        else:
            self.mount_element = js.document.createDocumentFragment()
            self.mount_parent.insertChild(self.mount_element, index)
        setattr(self.mount_element, _PY_TAG_ATTRIBUTE, self)

    def _mount_children(self):
        content = self.content()

        if isinstance(content, beepy.framework.Tag):
            content = (content,)
        elif isinstance(content, Iterable) and not isinstance(content, str) and content:
            content = list(content)
            for _child in content[:]:
                if not isinstance(_child, beepy.framework.Tag):
                    content = None
                    break
        else:
            content = None

        if content:
            for child in content:
                child.__mount__(self.mount_element, self.parent)
            self.children = content

    def __unmount__(self, element, parent):
        if self.mount_parent is not element:
            return

        if self.tag:
            element.safeRemoveChild(self.mount_element)
        # TODO: handle shadowRoot and documentFragment?

    def __render__(self):
        for renderer in self._current_render:
            if self.parent and renderer not in self.parent._dependents:
                self.parent._dependents.append(renderer)

        self._current_render.append(self)

        if self.children:
            for child in self.children:
                child.__render__()

            if self._current_render[-1] is self:
                self._current_render.pop()
            return

        result = self._render(self.content())
        if not isinstance(result, str):
            raise TypeError(f'Function {self.content} cannot return {result}!')

        if self.tag or (self.parent and self.parent._shadow_root):
            self.mount_element.innerHTML = result
        else:  # fragment can't be re-rendered
            self.mount_element.innerHTML = result
            current_html = self.mount_parent.innerHTML
            current_html_escaped = self._render(current_html)
            if result and result not in (current_html, current_html_escaped):
                if current_html and not (self.parent and self.parent._raw_html):
                    log.warn(
                        f'This html `{current_html}` will be replaces with this: `{result}`.\n'
                        'Maybe you must use beepy.Tag instead of beepy.tags.div, '
                        'or you used incorrect html tags like <br/> instead of <br>',
                    )
                self.mount_parent.innerHTML = result

        if self._current_render[-1] is self:
            self._current_render.pop()

    def __repr__(self):
        return f'<{self.parent}.{self.content.__name__}()>'


C = TypeVar('C')


class ChildRef(WebBase, Generic[C]):
    __slots__ = ('name', 'child', 'inline_def', '_cache')

    name: Optional[str]
    child: C
    _cache: dict[Context, C]

    def __init__(self, child: C, inline_def=False):
        self.name = None
        self.child = child
        self.inline_def = inline_def
        self._cache = {}

    def __repr__(self):
        return f'{type(self).__name__}(Tag.{self.name} = {self.child})'

    def __get__(self, instance: Optional[Context], owner: Optional[Type[Context]] = None) -> Union[ChildRef, C]:
        if instance is None:
            return self

        if (result := self._cache.get(instance)) is not None:
            return result

        self._cache[instance] = self.child
        return self.child

    def __set__(self, instance: Context, value: C):
        self._cache[instance] = value

    def __delete__(self, instance: Context):
        del self._cache[instance]

    def __set_name__(self, owner: Type[Tag], name: str):
        self.name = name

    @abstractmethod
    def _update_child(self, parent: Tag, index: int):
        pass

    def __render__(self, parent: Tag):
        self.__get__(parent).__render__()

    def __mount__(self, element, parent: Tag, index=None):
        self.__get__(parent).__mount__(element, parent, index)

    def __unmount__(self, element, parent: Tag):
        self.__get__(parent).__unmount__(element, parent)


class TagRef(ChildRef[Tag]):
    __slots__ = ()

    child: Tag

    def _update_child(self, parent, index):
        clone = self.__get__(parent).clone(parent)
        clone.__set_ref__(parent, self)
        self.__set__(parent, clone)


class ChildrenRef(ChildRef):
    __slots__ = ()

    child: Children

    def _update_child(self, parent, index):
        copy = self.__get__(parent).copy()
        copy.__set_parent__(parent, index, self)
        self.__set__(parent, copy)

    def __set__(self, instance, value):
        if isinstance(value, Children):
            super().__set__(instance, value)
        else:
            current_value = self.__get__(instance)
            current_value[:] = value


from beepy.framework import Tag


__all__ = ['CustomWrapper', 'StringWrapper', 'ContentWrapper', 'TagRef', 'ChildrenRef']
