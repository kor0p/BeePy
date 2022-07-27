from pyweb import Tag, mount, __CONFIG__
from pyweb.tags import Head
from pyweb.router import WithRouter, Router


class PageNotFound(Tag, WithRouter, name='error'):
    _base_content = '''
<h1>Error 404</h1>
<p>Page Not Found!</p>
'''

    def content(self):
        if not __CONFIG__['debug']:
            return self._base_content

        return self._base_content + (
            f'<p>Available routes: {list(self.router.routes.keys())}</p>'
        )


class AppRouter(Router):
    routes = {
        '/$': 'tabs.test_tabs',
        'context-menu/?$': 'context_menu.TestContext',
        'dynamic-url/?$': 'dynamic_url.DynamicURL',
        'modal/?$': 'modal.Test',
        'buttons/?$': 'buttons.View',
        'todos/?$': 'todos.TodoList',
        'timer/?$': 'count_down_timer.App',
    }

    fallback_tag_cls = PageNotFound


class App(Tag, name='app'):
    head = Head
    router = AppRouter()

    children = [
        head,
        router,
    ]


mount(App(), '#root')
