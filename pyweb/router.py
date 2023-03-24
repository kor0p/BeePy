from __future__ import annotations

import re
from re import Match
from typing import Union, Type
from dataclasses import dataclass

import js

from .framework import Tag, state, on
from .tags import a
from .types import Children
from .utils import lazy_import_cls, to_js


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

    def _load_children(self):
        self.components.clear()

        for path, tag_cls in self.routes.items():
            if match := re.search(path, js.location.pathname):
                self.components.append(
                    lazy_import_cls(tag_cls)(match=match, router=self)
                )
                if self.single_tag:
                    break

        if not self.components:
            if fallback := self.fallback_tag_cls:
                self.components.append(
                    lazy_import_cls(fallback)(match=None, router=self)
                )
            else:
                # TODO: maybe create PyWebError?
                raise ValueError('No route to use!')
