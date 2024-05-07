from beepy import Tag, __config__, import_css, mount, safe_html_content
from beepy.router import Link, Router, WithRouter
from beepy.tags import div

import_css('styles/main.css')


class PageNotFound(Tag, WithRouter, name='error'):
    # TODO: refactor this
    _base_content = '''
<h1>Error 404</h1>
<p>Page Not Found!</p>
'''

    @safe_html_content
    def content(self):
        if not __config__['debug']:
            return self._base_content

        return self._base_content + (f'<p>Available routes: {list(self.router.routes.keys())}</p>')


class BottomNavbar(div, WithRouter):
    class_ = 'bottom-navbar'

    children = [
        Link('⬅️ Back to examples', to=''),
    ]


class AppRouter(Router, name='main-app'):
    basename = '/e'
    routes = {
        '/': 'tabs.View',
        '/list-examples/': 'tabs.View',
        '/admin/': 'admin.Admin',
        '/context-menu/': 'context_menu.ContextExample',
        '/dynamic-url/': 'dynamic_url.DynamicURL',
        '/modal/': 'modal.View',
        '/buttons/': 'buttons.View',
        '/focus/': 'focus.App',
        '/highlight/': 'highlight.App',
        '/todos/': 'todos.TodoList',
        '/timer/': 'timer.App',
        '/text-sync/': 'text_sync.TextSyncExample',
        '/plot/': 'plot.App',
    }

    fallback_tag_cls = PageNotFound

    def add_tag_component(self, tag_cls, match, path):
        super().add_tag_component(tag_cls, match=match, path=path)
        if path == '$':
            return

        super().add_tag_component(BottomNavbar, match=match, path=path)


mount(AppRouter(), '#root')
