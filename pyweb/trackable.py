from typing import Union, SupportsIndex


class Trackable:
    def onchange(self):
        pass

    def _notify_add_one(self, key: int, added):
        raise NotImplementedError

    def _notify_remove_one(self, key: int, to_remove):
        raise NotImplementedError

    def _notify_add(self, key: Union[SupportsIndex, slice], added):
        raise NotImplementedError

    def _notify_remove(self, key: Union[SupportsIndex, slice], to_remove):
        raise NotImplementedError


class TrackableList(Trackable, list):
    def _notify_add(self, key: Union[SupportsIndex, slice], added: Union[tuple, list]):
        if isinstance(key, slice):
            for index, value in zip(range(key.start or 0, key.stop or len(self), key.step or 1), added):
                if index < 0:
                    index += len(self)
                self._notify_add_one(index, value)
        else:
            index = key.__index__()
            if index < 0:
                index += len(self)
            self._notify_add_one(index, added[0])
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
        self.onchange()

    def append(self, __object):
        super().append(__object)
        self._notify_add(-1, (self[-1], ))

    def clear(self):
        self._notify_remove(slice(0, len(self)), self)
        super().clear()

    def extend(self, __iterable):
        length = len(self)
        super().extend(__iterable)
        self._notify_add(slice(length, len(self)), self[length:len(self)])

    def insert(self, __index, __object):
        index = __index.__index__()
        super().insert(index, __object)
        self._notify_add(index, (self[index], ))

    def pop(self, __index=None):
        if __index is None:
            index = len(self) - 1
        else:
            index = __index.__index__()

        self._notify_remove(index, (self[index], ))
        super().pop(__index)

    def remove(self, __value):
        self._notify_remove(self.index(__value), (__value, ))
        super().remove(__value)

    def reverse(self):
        raise AttributeError('Not implemented yet!')

    def sort(self, *, key=..., reverse=...):
        raise AttributeError('Not implemented yet!')

    def __delitem__(self, key):
        self._notify_remove(key, self[key])
        super().__delitem__(key)

    def __iadd__(self, other):
        self.extend(other)

    def __imul__(self, n):
        length = len(self)
        super().__imul__(n)
        self._notify_add(slice(length, len(self)), self[length:len(self)])

    def __setitem__(self, key, value):
        self._notify_remove(key, self[key])
        super().__setitem__(key, value)
        self._notify_add(key, value)