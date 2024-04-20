from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from functools import wraps
from typing import TYPE_CHECKING

from beepy.trackable import TrackableList
from beepy.utils import __config__, js
from beepy.utils.common import escape_html

if TYPE_CHECKING:
    from beepy.children import ChildrenRef
    from beepy.framework import Tag


class AttrValue:
    """
    Extend this class to be able to use it as value in beepy.attr and children
    """

    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'AttrValue[{self.value}]'

    def __str__(self):
        return repr(self)

    @abstractmethod
    def __view_value__(self):
        """This method will be called on render, must return serializable value"""


class safe_html(str):
    __slots__ = ()

    def __html__(self) -> str:
        return self


def safe_html_content(function):
    @wraps(function)
    def content_wrapper(*args, **kwargs):
        return safe_html(function(*args, **kwargs))

    return content_wrapper


class Renderer:
    __slots__ = ()

    def _render(self, value: str | Iterable[str]) -> str:
        if isinstance(value, safe_html):
            return value.__html__()

        if isinstance(value, str):
            return escape_html(value, whitespace=__config__['html_replace_whitespaces'])

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
    def __mount__(self, element: js.HTMLElement, parent: Mounter, index: int | None = None):
        pass

    @abstractmethod
    def __unmount__(self, element: js.HTMLElement, parent: Mounter):
        pass


class WebBase(Renderer, Mounter, ABC):
    __slots__ = ()


class Children(WebBase, TrackableList):
    # TODO: extend Children from Context too?
    __slots__ = ('parent', 'parent_index', 'ref', 'mounted')

    parent: Tag | None
    parent_index: int
    ref: ChildrenRef | None
    mounted: bool

    def __init__(self, iterable=()):
        super().__init__(iterable)
        self.parent = None
        self.parent_index = 0
        self.ref = None
        self.mounted = False

    def _as_child(self, parent: Tag | None, *, exists_ok=False):
        from beepy.children import ChildrenRef

        if self.ref:
            if exists_ok:
                return self.ref
            else:
                raise TypeError(f'{self} already is child')
        ref = ChildrenRef(self)
        self._set_parent(parent, 0, ref)
        return ref

    def _set_parent(self, parent: Tag | None, index: int, ref: ChildrenRef):
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

        child._link_parent_attrs(self.parent)
        child.__mount__(self.parent._children_element, self.parent, key + self.parent_index)
        if self.parent._mount_finished_:
            child.__render__()

    def _notify_remove_one(self, _key: int, child: Tag):
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
            child._link_parent_attrs(parent)
            child.__mount__(element, parent, index)

    def __unmount__(self, element, parent):
        self.mounted = False

        for child in self:
            child.__unmount__(element, parent)


AttrType = None | str | int | bool | Iterable['AttrType'] | dict[str, 'AttrType'] | AttrValue  # Also: Tag | attr
ContentType = str | Iterable['ContentType'] | Renderer

__all__ = ['AttrType', 'ContentType', 'AttrValue', 'Renderer', 'Mounter', 'Children', 'safe_html', 'safe_html_content']
