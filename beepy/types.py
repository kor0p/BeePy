from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union, Iterable, ForwardRef
from functools import wraps

import beepy
from beepy.trackable import TrackableList
from beepy.utils import js, __CONFIG__
from beepy.utils.common import escape_html

attr = ForwardRef('attr')
Tag = ForwardRef('Tag')
ChildrenRef = ForwardRef('ChildrenRef')


class AttrValue:
    """
    Extend this class to be able to use it as value in beepy.attr and children
    """
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f'AttrValue[{self.value}]'

    @abstractmethod
    def __view_value__(self):
        """ This method will be called on render, must return serializable value """


class safe_html(str):
    def __html__(self) -> str:
        return self

    @classmethod
    def content(cls, function):
        @wraps(function)
        def content_wrapper(*args, **kwargs):
            return cls(function(*args, **kwargs))

        return content_wrapper


class Renderer:
    __slots__ = ()

    def _render(self, value: Union[str, Iterable[str]]) -> str:
        if isinstance(value, safe_html):
            return value.__html__()

        if isinstance(value, str):
            return escape_html(value, whitespace=__CONFIG__['html_replace_whitespaces'])

        if isinstance(value, Iterable):
            return ''.join(self._render(child) for child in value)

        return str(value)

    @abstractmethod
    def __render__(self, *a, **kw):
        # leave here any arguments to haven't problems when override this method
        pass


class Mounter:
    # TODO: add mount_element, mount_parent, etc?
    __slots__ = ()

    @abstractmethod
    def __mount__(self, element: js.HTMLElement, parent: Mounter, index: Optional[int] = None):
        pass

    @abstractmethod
    def __unmount__(self, element: js.HTMLElement, parent: Mounter):
        pass


class WebBase(Renderer, Mounter, ABC):
    __slots__ = ()


class Children(WebBase, TrackableList):
    # TODO: extend Children from Context too?
    __slots__ = ('parent', 'parent_index', 'ref', 'mounted')

    parent: Optional[Tag]
    parent_index: int
    ref: Optional[ChildrenRef]
    mounted: bool

    def __init__(self, iterable=()):
        super().__init__(iterable)
        self.parent = None
        self.parent_index = 0
        self.ref = None
        self.mounted = False

    def as_child(self, parent: Optional[Tag], exists_ok=False):
        if self.ref:
            if exists_ok:
                return self.ref
            else:
                raise TypeError(f'{self} already is child')
        ref = beepy.children.ChildrenRef(self)
        self.__set_parent__(parent, 0, ref)
        return ref

    def __set_parent__(self, parent: Optional[Tag], index: int, ref: ChildrenRef):
        self.parent = parent
        self.parent_index = index
        self.ref = ref
        if ref.inline_def:
            setattr(type(parent), ref.name, self)

    def onchange_notify(self):
        if not self.parent or not self.parent.parent:
            return

        for trigger in self.onchange_triggers:
            trigger(self.parent)

    def _notify_add_one(self, key: int, child: Tag):
        if not self.mounted and not self.parent:
            return

        child.link_parent_attrs(self.parent)
        child.__mount__(self.parent._children_element, self.parent, key + self.parent_index)
        if self.parent._mount_finished_:
            child.__render__()

    def _notify_remove_one(self, key: int, child: Tag):
        if not self.mounted and not self.parent:
            return

        child.__unmount__(self.parent._children_element, self.parent)

    def __render__(self):
        for child in self:
            child.__render__()

    def __mount__(self, element, parent: Tag, index=None):
        self.mounted = True

        if index is not None:
            index += self.parent_index
        for child in self:
            child.link_parent_attrs(parent)
            child.__mount__(element, parent, index)

    def __unmount__(self, element, parent):
        self.mounted = False

        for child in self:
            child.__unmount__(element, parent)


AttrType = Union[None, str, int, bool, Iterable['AttrType'], dict[str, 'AttrType'], AttrValue, Tag, attr]
ContentType = Union[str, Iterable, Renderer]

__all__ = ['AttrType', 'ContentType', 'AttrValue', 'Renderer', 'Mounter', 'Children']
