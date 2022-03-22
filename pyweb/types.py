from __future__ import annotations

import js

from typing import Optional, Union, Iterable, ForwardRef

from .trackable import TrackableList


Tag = ForwardRef('Tag')
Children = ForwardRef('Children')


class AttrValue:
    """
    Extend this class to be able to use it as value in pyweb.attr and children
    """

    def __view_value__(self):
        """ This method will be called on render, must return serializable value """
        raise NotImplementedError


class Renderer:
    __slots__ = ()

    def _render(self, string: Union[str, Iterable[str, ...]]):
        if isinstance(string, str):
            return string

        if isinstance(string, Iterable):
            return ''.join(self._render(child) for child in string)

        return str(string)

    def __render__(self, *a, **kw):
        # leave here any arguments to haven't problems when override this method
        raise NotImplementedError


class Mounter:
    # TODO: add mount_element, mount_parent, etc?
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


AttrType = Union[None, str, int, bool, Iterable['AttrType'], dict[str, 'AttrType'], Tag]
ContentType = Union[str, Iterable, Renderer]


from .children import Children
from .framework import Tag

__all__ = ['AttrType', 'ContentType', 'AttrValue', 'Renderer', 'Mounter', '_ChildrenList']
