from __future__ import annotations

from typing import Optional, Any, Callable, Union, Type

import js

from .types import Tag, Renderer, Mounter, _ChildrenList, ContentType
from .utils import log, _current


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

        result = self._render(result).strip()
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
        return f'<{self.parent}.{self.content.__name__}()>'


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
        return f'{type(self).__name__}(Tag.{self.name} = {self.child})'

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


__all__ = ['ContentWrapper', 'ChildRef', 'Children']
