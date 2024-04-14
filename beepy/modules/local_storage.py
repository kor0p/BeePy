from __future__ import annotations

import json
from collections.abc import MutableMapping

from beepy.utils import js


class LocalStorage(MutableMapping):
    __slots__ = ('prefix',)

    def __init__(self, key: str):
        if not key.strip():
            raise TypeError('Local Storage key cannot be empty')

        self.prefix = key

    def __contains__(self, key):
        return (self.prefix + key) in js.localStorage

    def __getitem__(self, key):
        return json.loads(js.localStorage.getItem(self.prefix + key) or 'null')

    def __setitem__(self, key, value):
        js.localStorage.setItem(self.prefix + key, json.dumps(value))

    def __delitem__(self, key):
        js.localStorage.removeItem(self.prefix + key)

    def __iter__(self):
        return (key.removeprefix(self.prefix) for key in js.Object.keys(js.localStorage) if key.startswith(self.prefix))

    def __len__(self):
        return len(tuple(iter(self)))


class _GlobalLocalStorage(LocalStorage):
    def __init__(self):
        super().__init__('-')
        self.prefix = ''


GlobalLocalStorage = _GlobalLocalStorage()


__all__ = ['LocalStorage', 'GlobalLocalStorage']
