from __future__ import annotations

# [PYWEB IGNORE START]
import js
from .framework import attr, state, on
from .style import style
from .tags import div, hr, ul, li
# [PYWEB IGNORE END]


class MenuDivider(hr):
    default_style = style(
        border_bottom='1px solid #eee',
        margin='10px 0',
    )


class MenuItem(li):
    id: str = state()

    default_style = style(styles={
        'padding': '0.5em 1em',
        'cursor': 'pointer',
        'display': 'flex',
        'align-items': 'center',
        '&:hover': {
            'background-color': '#2d2d2d',
            'border-left': '4px solid #333',
        }
    })

    def __set_ref__(self, ref):
        super().__set_ref__(ref)
        self.id = ref.name


class ContextMenu(ul):
    visible: bool = attr(False)

    pos_x: int = state(0)
    pos_y: int = state(0)

    dynamic_styles = style(
        left='{pos_x}px',
        top='{pos_y}px',
    )

    default_style = style(styles={
        'background-color': '#353535',
        'font-size': '24px',
        'border-radius': '2px',
        'padding': '5px 0 5px 0',
        'width': '180px',
        'height': 'auto',
        'margin': 0,
        # use absolute positioning
        'position': 'absolute',
        'list-style': 'none',
        'box-shadow': '0 0 20px 0 #222',
        'opacity': 0,
        'transition': 'opacity 0.2s linear',

        '&[visible]': {
            'opacity': 1,
        }
    })

    def set_pos(self, x=0, y=0):
        el = self.mount_element

        if x + el.offsetWidth > js.innerWidth:
            x -= el.offsetWidth

        if y + el.offsetHeight > js.innerHeight:
            y -= el.offsetHeight

        self.pos_x = x
        self.pos_y = y
        self.visible = True


class ContextMenuHandler(div):
    menu = ContextMenu()

    default_style = style(
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
        self.menu.visible = False

    @on
    def contextmenu(self, event):
        event.preventDefault()
        self.menu.set_pos(event.pageX, event.pageY)
