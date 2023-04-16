from __future__ import annotations

import re
from re import Match
from typing import Union, Type

import js

from pyweb.framework import Tag, state
from pyweb.types import Children
from pyweb.utils import lazy_import_cls


class WithRouter:
    match: Match = state(move_on=True)
    router: Router = state(move_on=True)


class Router(Tag, name='router'):
    routes: dict[str, Union[str, Type[Tag]]] = {
        # r'/$': Tag,
        # r'/app/(?P<id>.*)$': 'app.App',  # lazy import!
    }

    fallback_tag_cls = None
    single_tag = True

    components = Children()

    children = [
        components,
    ]

    def mount(self):
        self._load_children()

    def add_tag_component(self, tag_cls: str | Type[Tag], **kwargs):
        tag_cls: Type[Tag] = lazy_import_cls(tag_cls)
        if issubclass(tag_cls, WithRouter):
            kwargs['router'] = self
        self.components.append(tag_cls(**kwargs))

    def _load_children(self):
        self.components.clear()

        for path, tag_cls in self.routes.items():
            if match := re.search(path, js.location.pathname):
                self.add_tag_component(tag_cls, match=match)
                if self.single_tag:
                    break

        if not self.components:
            if fallback := self.fallback_tag_cls:
                self.add_tag_component(fallback, match=None)
            else:
                # TODO: maybe create PyWebError?
                raise ValueError('No route to use!')
