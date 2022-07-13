from __future__ import annotations

import js

from abc import ABC, abstractmethod
from typing import Optional, Union, Iterable, ForwardRef

from .trackable import TrackableList


Tag = ForwardRef('Tag')
ChildrenRef = ForwardRef('ChildrenRef')


class AttrValue:
    """
    Extend this class to be able to use it as value in pyweb.attr and children
    """
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f'AttrValue[{self.value}]'

    @abstractmethod
    def __view_value__(self):
        """ This method will be called on render, must return serializable value """


class Renderer:
    __slots__ = ()

    def _render(self, string: Union[str, Iterable[str, ...]]):
        if isinstance(string, str):
            return string

        if isinstance(string, Iterable):
            return ''.join(self._render(child) for child in string)

        return str(string)

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
    parent_index: Optional[int]
    ref: Optional[ChildrenRef]
    mounted: bool

    def __init__(self, iterable=()):
        super().__init__(iterable)
        self.parent = None
        self.parent_index = None
        self.ref = None
        self.mounted = False

    def as_child(self, exists_ok=False):
        if self.ref:
            if exists_ok:
                return self.ref
            else:
                raise TypeError(f'{self} already is child')
        ref = ChildrenRef(self)
        self.__set_parent__(None, None, ref)
        return ref

    def __set_parent__(self, parent: Optional[Tag], index: Optional[int], ref: ChildrenRef):
        self.parent = parent
        self.parent_index = index
        self.ref = ref

    def onchange_notify(self):
        if not hasattr(self.parent, 'parent'):
            return

        for trigger in self.onchange_triggers:
            trigger(self.parent)

    def _notify_add_one(self, key: int, child: Tag):
        if not self.mounted and not self.parent:
            return

        child.__mount__(self.parent.children_element, self.parent, key + self.parent_index)
        child.__render__()

    def _notify_remove_one(self, key: int, child: Tag):
        if not self.mounted and not self.parent:
            return

        child.__unmount__(self.parent.children_element, self.parent)

    def __render__(self):
        for child in self:
            child.__render__()

    def __mount__(self, element, parent: Tag, index=None):
        self.mounted = True

        if index is not None:
            index += self.parent_index
        for child in self:
            child.__mount__(element, parent, index)

    def __unmount__(self, element, parent):
        self.mounted = False

        for child in self:
            child.__unmount__(element, parent)


AttrType = Union[None, str, int, bool, Iterable['AttrType'], dict[str, 'AttrType'], AttrValue]
ContentType = Union[str, Iterable, Renderer]


from .children import ChildrenRef
from .framework import Tag

__all__ = ['AttrType', 'ContentType', 'AttrValue', 'Renderer', 'Mounter', 'Children']
