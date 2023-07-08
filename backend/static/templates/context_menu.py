import js

from beepy import Style, __version__
from beepy.tags import p, Head
from beepy.context_menu import MenuDivider, MenuItem, ContextMenu, ContextMenuHandler

Head.title = 'Context Menu example'


class Menu(ContextMenu):
    children = [
        share_to := MenuItem('Share To...'),
        MenuItem('Cut'),
        MenuItem('Copy'),
        MenuItem('Paste'),
        MenuDivider(),
        refresh := MenuItem('Refresh'),
        MenuItem('Exit'),
    ]

    @share_to.on('click')
    def open_share(self, event):
        js.open(f'https://t.me/share/url?url={js.location.href}&text=Yay! It\'s BeePy v{__version__}', '_blank')

    @refresh.on('click')
    def refresh_page(self, event):
        js.location.reload()


class ContextExample(ContextMenuHandler, name='context-example', content_tag=p()):
    style = Style(
        font_size='48px',
    )

    children = [
        menu := Menu(),
    ]

    _content = 'Right click somewhere on the page...'
