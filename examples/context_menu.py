import js

from pyweb import mount
from pyweb.style import style
from pyweb.tags import p
from pyweb.context_menu import MenuDivider, MenuItem, ContextMenu, ContextMenuHandler


class Menu(ContextMenu):
    share_to = MenuItem('Share To...')
    cut = MenuItem('Cut')
    copy = MenuItem('Copy')
    paste = MenuItem('Paste')
    _ = MenuDivider()
    refresh = MenuItem('Refresh')
    exit = MenuItem('Exit')

    @share_to.on('click')
    def open_share(self, event):
        js.open('https://t.me/kor0p', '_blank')

    @refresh.on('click')
    def refresh_page(self, event):
        js.location.reload()


class TestContext(ContextMenuHandler, name='test-context', content_tag=p()):
    menu = Menu()

    style = style(
        font_size='48px',
    )

    _content = 'Right click somewhere on the page...'


mount(
    TestContext(),
    '#pyweb',
)
