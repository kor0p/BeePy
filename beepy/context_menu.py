from __future__ import annotations

import js
from beepy.framework import attr, state, on
from beepy.style import Style
from beepy.tags import div, hr, ul, li, Body


class MenuDivider(hr):
    default_style = Style(
        border_bottom='1px solid #eee',
        margin='10px 0',
    )


class MenuItem(li):
    default_style = Style(styles={
        'padding': '0.5em 1em',
        'cursor': 'pointer',
        'display': 'flex',
        'align-items': 'center',
        '&:hover': {
            'background-color': '#2d2d2d',
            'border-left': '4px solid #333',
        }
    })


class ContextMenu(ul):
    visible = attr(False)

    pos_x = state(0)
    pos_y = state(0)

    dynamic_styles = Style(
        left='{pos_x}px',
        top='{pos_y}px',
    )

    default_style = Style(styles={
        'visibility': 'hidden',
        'background-color': '#353535',
        'font-size': '24px',
        'border-radius': '2px',
        'padding': '5px 0 5px 0',
        'width': '180px',
        'height': 'auto',
        'margin': 0,
        'z-index': 50,
        # use absolute positioning
        'position': 'absolute',
        'list-style': 'none',
        'box-shadow': '0 0 20px 0 #222',
        'opacity': 0,
        'transition': '0.2s',

        '&[visible]': {
            'opacity': 1,
            'visibility': 'visible',
        }
    })

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def set_pos(self, x=0, y=0):
        el = self.mount_element

        if x + el.offsetWidth > js.innerWidth:
            x -= el.offsetWidth

        if y + el.offsetHeight > js.innerHeight:
            y -= el.offsetHeight

        self.pos_x = x
        self.pos_y = y
        self.show()

    def __mount__(self, element, parent, index=None):
        super().__mount__(Body.mount_element, Body)

    def __unmount__(self, element, parent, _unsafe=False):
        return super().__unmount__(element, parent, _unsafe=True)


class ContextMenuHandler(div):
    menu: ContextMenu

    default_style = Style(
        position='absolute',
        inset=0,
        width='100%',
        height='100%',
        display='flex',
        justifyContent='center',
        alignItems='center',
    )

    @on
    def click(self, event):
        self.menu.hide()

    @on('contextmenu.prevent')
    def show_menu(self, event):
        self.menu.set_pos(event.pageX, event.pageY)


__all__ = ['MenuDivider', 'MenuItem', 'ContextMenu', 'ContextMenuHandler']
