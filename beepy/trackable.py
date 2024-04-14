from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import SupportsIndex

from beepy.utils.common import Locker


class Trackable(ABC):
    __slots__ = ()

    onchange_triggers: list[Callable]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.onchange_triggers = []
        self.onchange_locker = Locker('Disable onchange()')

    @abstractmethod
    def onchange_notify(self):
        pass

    def onchange(self, handler=None):
        if handler is None:
            if not self.onchange_locker:
                self.onchange_notify()
        else:
            if handler in self.onchange_triggers:
                raise AttributeError('This @onchange trigger is already set')
            self.onchange_triggers.append(handler)
            return handler

    @abstractmethod
    def _notify_add_one(self, key: int, added):
        pass

    @abstractmethod
    def _notify_remove_one(self, key: int, to_remove):
        pass

    @abstractmethod
    def _notify_add(self, key: SupportsIndex | slice, added):
        pass

    @abstractmethod
    def _notify_remove(self, key: SupportsIndex | slice, to_remove):
        pass

    @abstractmethod
    def _notify_post_remove(self):
        pass


class TrackableList(Trackable, list):
    __slots__ = ('onchange_triggers', 'onchange_locker')

    def _notify_add(self, key: SupportsIndex | slice, added: Iterable):
        length = len(self)
        if isinstance(key, slice):
            for index, value in zip(range(key.start or 0, key.stop or length, key.step or 1), added, strict=True):
                if index < 0:
                    index += length  # noqa: PLW2901
                self._notify_add_one(index, value)
        else:
            index = key.__index__()
            if index < 0:
                index += length
            self._notify_add_one(index, added[0])
        if added:
            self.onchange()

    def _notify_remove(self, key: SupportsIndex | slice, to_remove: tuple | list):
        if isinstance(key, slice):
            for index, value in reversed(
                tuple(zip(range(key.start or 0, key.stop or len(self), key.step or 1), to_remove, strict=True))
            ):
                if index < 0:
                    index += len(self)  # noqa: PLW2901
                self._notify_remove_one(index, value)
        else:
            index = key.__index__()
            if index < 0:
                index += len(self)
            self._notify_remove_one(index, to_remove[0])

    def append(self, __object):
        super().append(__object)

        if not self.onchange_locker:
            self._notify_add(-1, (self[-1],))

    def clear(self):
        length = len(self)
        if not self.onchange_locker:
            self._notify_remove(slice(0, length), self)
        super().clear()
        if not self.onchange_locker and length:
            self._notify_post_remove()
            self.onchange()

    def extend(self, __iterable):
        if self.onchange_locker:
            super().extend(__iterable)
            return

        length = len(self)
        super().extend(__iterable)
        self._notify_add(slice(length, len(self)), self[length : len(self)])

    def insert(self, __index, __object):
        if self.onchange_locker:
            super().insert(__index, __object)
            return

        index = __index.__index__()
        super().insert(index, __object)
        self._notify_add(index, (self[index],))

    def pop(self, __index=None):
        if self.onchange_locker:
            return super().pop(__index)

        index = len(self) - 1 if __index is None else __index.__index__()

        self._notify_remove(index, (self[index],))
        result = super().pop(__index)
        self._notify_post_remove()
        self.onchange()
        return result

    def remove(self, __value):
        if self.onchange_locker:
            super().remove(__value)
            return

        self._notify_remove(self.index(__value), (__value,))
        super().remove(__value)
        self._notify_post_remove()
        self.onchange()

    def copy(self):
        result = type(self)(super().copy())
        result.onchange_triggers = self.onchange_triggers.copy()
        return result

    def reverse(self):
        if self.onchange_locker:
            super().reverse()
            return

        length = len(self)
        self._notify_remove(slice(0, length), self)

        super().reverse()

        if length:
            self._notify_post_remove()

        self._notify_add(slice(0, len(self)), self)

    def sort(self, *, key=..., reverse=...):
        if self.onchange_locker:
            super().sort(key=key, reverse=reverse)
            return

        # TODO: rewrite this after `key=` implemented
        length = len(self)
        self._notify_remove(slice(0, length), self)

        super().sort(key=key, reverse=reverse)

        if length:
            self._notify_post_remove()

        self._notify_add(slice(0, len(self)), self)

    def __delitem__(self, key):
        if self.onchange_locker:
            super().__delitem__(key)
            return

        to_remove = self[key]
        if not isinstance(to_remove, list):
            to_remove = (to_remove,)

        self._notify_remove(key, to_remove)
        super().__delitem__(key)
        if to_remove:
            self._notify_post_remove()
            self.onchange()

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __imul__(self, n):
        if self.onchange_locker:
            return super().__imul__(n)

        length = len(self)
        n = n.__index__()
        if n <= 0:
            self._notify_remove(slice(0, length), self)
        super().__imul__(n)
        if n <= 0:
            if length:
                self._notify_post_remove()
        else:
            self._notify_add(slice(length, len(self)), self[length : len(self)])
        return self

    def __setitem__(self, key, value):
        if self.onchange_locker:
            super().__setitem__(key, value)
            return

        to_remove = self[key]
        if not isinstance(to_remove, list):
            to_remove = (to_remove,)

        self._notify_remove(key, to_remove)
        super().__setitem__(key, value)
        if to_remove:
            self._notify_post_remove()

        added = value
        if not isinstance(added, Iterable):
            added = (added,)
        self._notify_add(key, added)

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'


__all__ = ['Trackable', 'TrackableList']
