import js

from pyweb import mount
from pyweb.style import style
from pyweb.tags import p, Head
from pyweb.context_menu import MenuDivider, MenuItem, ContextMenu, ContextMenuHandler


class Menu(ContextMenu):
    children = [
        MenuItem('Share To...'),
        MenuItem('Cut'),
        MenuItem('Copy'),
        MenuItem('Paste'),
        MenuDivider(),
        MenuItem('Refresh'),
        MenuItem('Exit')
    ]

    # get as references
    share_to = children[0]
    refresh = children[5]

    @share_to.on('click')
    def open_share(self, event):
        js.open('https://t.me/kor0p', '_blank')

    @refresh.on('click')
    def refresh_page(self, event):
        js.location.reload()


class TestContext(ContextMenuHandler, name='test-context', content_tag=p()):
    style = style(
        font_size='48px',
    )

    menu = Menu()

    children = [
        menu,
    ]

    _content = 'Right click somewhere on the page...'

    def mount(self):
        Head.title = 'Context Menu example'


if __name__ == '__pyweb_root__':
    mount(TestContext(), '#pyweb')
