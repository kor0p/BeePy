from beepy import Style, __version__
from beepy.modules.context_menu import ContextMenu, ContextMenuHandler, MenuDivider, MenuItem
from beepy.tags import Head, p
from beepy.utils import js

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
    def open_share(self):
        js.open(f"https://t.me/share/url?url={js.location.href}&text=Yay! It's BeePy v{__version__}", '_blank')

    @refresh.on('click')
    def refresh_page(self):
        js.location.reload()


class ContextExample(ContextMenuHandler, name='context-example', content_tag=p()):
    style = Style(
        font_size='48px',
    )

    children = [
        menu := Menu(),
    ]

    _content = 'Right click somewhere on the page...'
