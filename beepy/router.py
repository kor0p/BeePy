from __future__ import annotations

import re
from dataclasses import dataclass
from re import Match

from beepy import Tag
from beepy.attrs import html_attr, state
from beepy.listeners import on
from beepy.tags import a
from beepy.types import Children
from beepy.utils import js
from beepy.utils.dev import _debugger
from beepy.utils.internal import lazy_import_cls, reload_requirements
from beepy.utils.js_py import push_url


class WithRouter:
    match: Match = state(move_on=True)
    router: Router = state(move_on=True)


@dataclass
class Path:
    # TODO: move to utils?
    pathname: str = ''
    search: str = ''
    hash: str = ''

    @classmethod
    def parse(cls, path: str):
        result = cls()

        if path:
            if '#' in path:
                path, hash = path.split('#', 1)
                result.hash = '#' + hash

            if '?' in path:
                path, search = path.split('?', 1)
                result.search = '?' + search

            if path:
                result.pathname = path

        return result

    @classmethod
    def parse_to(cls, to):
        if not to:
            return '/'
        if isinstance(to, str):
            to = cls.parse(to)
        return to.pathname

    def iter_search(self):
        for search_element in self.search[1:].split('&'):
            if not search_element:
                continue

            key, value = search_element.split('=', 1)
            yield key, js.decodeURIComponent(value)

    def push_state(self):
        url = js.URL.new(js.location.origin + self.pathname + self.hash)

        if (not url.hash and url.href[-1] == '#') or url.hash == '#':
            url.href = url.href[:-1]

        for key, value in self.iter_search():
            url.searchParams.set(key, value)  # modifies url.href

        push_url(url, path=self.__dict__)


class Link(a, WithRouter):
    to = state(type=str, required=True)
    href = html_attr(type=str)

    @to.on('init', 'change')
    def to_changed(self, value):
        if self.router:
            value = self.router.basename + value
        self.href = Path.parse_to(value)

    @on('click.prevent')
    async def navigate(self):
        Path.parse(self.router.basename + self.to).push_state()
        await self.router._history_refresh()


class Router(Tag):
    basename = ''
    routes: dict[str, str | type[Tag]] = {
        # r'/$': Tag,
        # r'/app/(?P<id>.*)$': 'app.App',  # lazy import!
    }

    fallback_tag_cls = None
    single_tag = True

    children = [
        components := Children(),
    ]

    def pre_mount(self):
        self._load_children()

    @on('popstate')
    async def _history_refresh(self):
        js.beepy.startLoading(mountPoint=self._root_parent.mount_element)
        await reload_requirements()
        self._load_children()
        js.beepy.stopLoading()

    def import_tag_component(self, tag_cls: str | type[Tag], match, **kwargs):
        try:
            tag_cls: type[Tag] = lazy_import_cls(tag_cls)
        except ModuleNotFoundError as e:
            _debugger(e)
            raise

        if issubclass(tag_cls, WithRouter):
            kwargs |= {'router': self, 'match': match}
        return tag_cls(**kwargs)

    def add_tag_component(self, tag_cls: str | type[Tag], match, path):  # noqa: ARG002 - arguments for overriding
        self.components.append(self.import_tag_component(tag_cls, match=match))

    def _load_children(self):
        self._current_render.clear()

        old_components = list(self.components)

        with self.components._disable_onchange:  # can Locker also be descriptor with auto-replace as in last two lines?
            self.components.clear()

            for path, tag_cls in self.routes.items():
                if match := re.search(self.basename + path, js.location.pathname):
                    self.add_tag_component(tag_cls, match=match, path=path)
                    if self.single_tag:
                        break

            if not self.components:
                if fallback := self.fallback_tag_cls:
                    self.add_tag_component(fallback, match=None, path=None)
                else:
                    # TODO: maybe create BeePyError?
                    raise ValueError('No route to use!')

            for child in self.components:
                child.link_parent_attrs(self)
                args, kwargs = child.args_kwargs
                kwargs = child._attrs_defaults | kwargs
                child.init(*args, _load_children=False, **kwargs)

            new_components, self.components = list(self.components), old_components
        self.components[:] = new_components  # triggers correct onchange handlers
