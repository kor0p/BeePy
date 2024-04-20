from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Generic, Self, TypeVar, overload

import beepy
from beepy.components import Component
from beepy.types import Children, ContentType, Renderer, WebBase
from beepy.utils import js, log
from beepy.utils.internal import _py_tag_attribute

if TYPE_CHECKING:
    from beepy.context import Context
    from beepy.framework import Tag
else:
    Tag = None


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

    content: Callable[[], ContentType | Tag]
    tag: Tag | None
    mount_element: js.HTMLElement | None
    _current_render: list[Renderer]
    parent: Tag | None
    mount_parent: js.HTMLElement | None
    children: list[Tag] | None

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
        if self.tag:
            self.mount_element = self.tag._clone(parent).mount_element
            self.mount_parent.insertChild(self.mount_element, index)
        else:
            self.mount_element = js.document.createDocumentFragment()
            self.mount_parent.insertChild(self.mount_element, index)
        setattr(self.mount_element, _py_tag_attribute, self)

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

        if self.tag:
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

    name: str | None
    child: C
    _cache: dict[Context, C]

    def __init__(self, child: C, *, inline_def=False):
        self.name = None
        self.child = child
        self.inline_def = inline_def
        self._cache = {}

    def __repr__(self):
        return f'{type(self).__name__}(Tag.{self.name} = {self.child})'

    @overload
    def __get__(self, instance: None, owner: type[Context]) -> Self: ...

    @overload
    def __get__(self, instance: Context | Tag, owner: type[Context] | None = None) -> C: ...

    def __get__(self, instance: Context | Tag | None, owner: type[Context] | None = None) -> Self | C:
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

    def __set_name__(self, owner: type[Tag], name: str):
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


class ComponentRef(ChildRef[Component]):
    __slots__ = ()

    child: Component

    def _update_child(self, parent: Tag, index):  # noqa: ARG002 - arguments for overriding
        clone = self.__get__(parent)._clone(parent)
        clone._set_ref(parent, self)
        self.__set__(parent, clone)
        return clone


class TagRef(ComponentRef, ChildRef[Tag]):
    __slots__ = ()

    child: Tag


class ChildrenRef(ChildRef):
    __slots__ = ()

    child: Children

    def _update_child(self, parent, index):
        copy = self.__get__(parent).copy()
        copy._set_parent(parent, index, self)
        self.__set__(parent, copy)
        return copy

    def __set__(self, instance, value):
        if isinstance(value, Children):
            super().__set__(instance, value)
        else:
            self.__get__(instance)[:] = value


__all__ = ['CustomWrapper', 'StringWrapper', 'ContentWrapper', 'TagRef', 'ChildrenRef']
