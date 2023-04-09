import js

from pyweb import Style, __version__
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
        MenuItem('Exit'),
    ]

    # get as references
    share_to, _, _, _, _, refresh, _ = children

    @share_to.on('click')
    def open_share(self, event):
        js.open(f'https://t.me/share/url?url={js.location.href}&text=Yay! It\'s PyWeb v{__version__}', '_blank')

    @refresh.on('click')
    def refresh_page(self, event):
        js.location.reload()


class TestContext(ContextMenuHandler, name='test-context', content_tag=p()):
    style = Style(
        font_size='48px',
    )

    menu = Menu()

    children = [
        menu,
    ]

    _content = 'Right click somewhere on the page...'

    def mount(self):
        Head.title = 'Context Menu example'
