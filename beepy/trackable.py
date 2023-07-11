from abc import ABC, abstractmethod
from typing import Union, SupportsIndex, Callable

from beepy.utils.common import Locker


class Trackable(ABC):
    __slots__ = ()

    onchange_triggers: list[Callable]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.onchange_triggers = []
        self._disable_onchange = Locker('Disable onchange()')

    def onchange_notify(self):
        pass

    def onchange(self, handler=None):
        if handler is None:
            if not self._disable_onchange:
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
    def _notify_add(self, key: Union[SupportsIndex, slice], added):
        pass

    @abstractmethod
    def _notify_remove(self, key: Union[SupportsIndex, slice], to_remove):
        pass

    def _notify_post_remove(self):
        self.onchange()


class TrackableList(Trackable, list):
    __slots__ = ('onchange_triggers', '_disable_onchange')

    def _notify_add(self, key: Union[SupportsIndex, slice], added: Union[tuple, list]):
        length = len(self)
        if isinstance(key, slice):
            for index, value in zip(range(key.start or 0, key.stop or length, key.step or 1), added):
                if index < 0:
                    index += length
                self._notify_add_one(index, value)
        else:
            index = key.__index__()
            if index < 0:
                index += length
            self._notify_add_one(index, added[0])
        if added:
            self.onchange()

    def _notify_remove(self, key: Union[SupportsIndex, slice], to_remove: Union[tuple, list]):
        if isinstance(key, slice):
            for index, value in reversed(list(
                zip(range(key.start or 0, key.stop or len(self), key.step or 1), to_remove)
            )):
                if index < 0:
                    index += len(self)
                self._notify_remove_one(index, value)
        else:
            index = key.__index__()
            if index < 0:
                index += len(self)
            self._notify_remove_one(index, to_remove[0])

    def append(self, __object):
        super().append(__object)

        if not self._disable_onchange:
            self._notify_add(-1, (self[-1], ))

    def clear(self):
        length = len(self)
        if not self._disable_onchange:
            self._notify_remove(slice(0, length), self)
        super().clear()
        if not self._disable_onchange:
            if length:
                self._notify_post_remove()

    def extend(self, __iterable):
        if self._disable_onchange:
            super().extend(__iterable)
            return

        length = len(self)
        super().extend(__iterable)
        self._notify_add(slice(length, len(self)), self[length:len(self)])

    def insert(self, __index, __object):
        if self._disable_onchange:
            super().insert(__index, __object)
            return

        index = __index.__index__()
        super().insert(index, __object)
        self._notify_add(index, (self[index], ))

    def pop(self, __index=None):
        if self._disable_onchange:
            return super().pop(__index)

        if __index is None:
            index = len(self) - 1
        else:
            index = __index.__index__()

        self._notify_remove(index, (self[index], ))
        result = super().pop(__index)
        self._notify_post_remove()
        return result

    def remove(self, __value):
        if self._disable_onchange:
            super().remove(__value)
            return

        self._notify_remove(self.index(__value), (__value, ))
        super().remove(__value)
        self._notify_post_remove()

    def copy(self):
        result = type(self)(super().copy())
        result.onchange_triggers = self.onchange_triggers.copy()
        return result

    def reverse(self):
        raise AttributeError('Not implemented yet!')

    def sort(self, *, key=..., reverse=...):
        raise AttributeError('Not implemented yet!')

    def __delitem__(self, key):
        if self._disable_onchange:
            super().__delitem__(key)
            return

        to_remove = self[key]
        if not isinstance(to_remove, (tuple, list)):
            to_remove = (to_remove,)

        self._notify_remove(key, to_remove)
        super().__delitem__(key)
        if to_remove:
            self._notify_post_remove()

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __imul__(self, n):
        if self._disable_onchange:
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
            self._notify_add(slice(length, len(self)), self[length:len(self)])
        return self

    def __setitem__(self, key, value):
        if self._disable_onchange:
            super().__setitem__(key, value)
            return

        to_remove = self[key]
        if not isinstance(to_remove, (tuple, list)):
            to_remove = (to_remove,)

        self._notify_remove(key, to_remove)
        super().__setitem__(key, value)
        # TODO: prevent doubling calls of onchange_notify
        if to_remove:
            self._notify_post_remove()

        added = value
        if not isinstance(added, (tuple, list)):
            added = (added,)
        self._notify_add(key, added)

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'


__all__ = ['Trackable', 'TrackableList']
