from beepy import __CONFIG__, Style, Tag, mount, safe_html_content
from beepy.router import Link, Router, WithRouter
from beepy.tags import Head, div

Style.import_file('styles/main.css')


class PageNotFound(Tag, WithRouter, name='error'):
    _base_content = '''
<h1>Error 404</h1>
<p>Page Not Found!</p>
'''

    @safe_html_content
    def content(self):
        if not __CONFIG__['debug']:
            return self._base_content

        return self._base_content + (f'<p>Available routes: {list(self.router.routes.keys())}</p>')


class BottomNavbar(div, WithRouter):
    class_ = 'bottom-navbar'

    children = [
        Link('⬅️ Back to examples', to=''),
    ]


class AppRouter(Router):
    basename = '/e/'
    routes = {
        '$': 'tabs.View',
        'list-examples': 'tabs.View',
        'admin': 'admin.Admin',
        'context-menu': 'context_menu.ContextExample',
        'dynamic-url': 'dynamic_url.DynamicURL',
        'modal': 'modal.View',
        'buttons': 'buttons.View',
        'focus': 'focus.App',
        'highlight': 'highlight.App',
        'todos': 'todos.TodoList',
        'timer': 'timer.App',
        'text-sync': 'text_sync.TextSyncExample',
        'latex': 'latex.HighlightLaTeX',
        'plot': 'plot.App',
    }

    fallback_tag_cls = PageNotFound

    def add_tag_component(self, tag_cls, match, path, **kwargs):
        super().add_tag_component(tag_cls, match=match, path=path, **kwargs)
        if path == '$':
            return

        super().add_tag_component(BottomNavbar, match=match, path=path, **kwargs)


class App(Tag, name='main-app'):
    children = [
        Head,
        AppRouter(),
    ]


mount(App(), '#root')
