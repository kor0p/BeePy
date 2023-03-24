from typing import Callable

from .framework import Tag, attr, state, on
from .style import Style
from .tags import div, button, Body


class Modal(Tag, name='modal', content_tag='h2', children_tag='modal-content'):
    visible = attr(False)
    on_close = state(type=Callable[[bool], None])  # TODO: add example

    default_style = Style(styles={
        'position': 'absolute',
        'inset': 0,
        'width': '100%',
        'height': '100%',
        'display': 'flex',
        ('justify-content', 'justify-items', 'align-items'): 'center',
        'background-color': 'rgba(255, 255, 255, 0.2)',
        'opacity': 0,
        'visibility': 'hidden',
        'transition': 'opacity 0.2s, visibility 0.2s',
        '&[visible]': {
            'opacity': 1,
            'visibility': 'visible',
        },
        'modal-content': {
            'position': 'absolute',
            'padding': '5%',
            ('width', 'height'): 'fit-content',
            'display': 'flex',
            'flex-direction': 'column',
            ('justify-content', 'justify-items', 'align-items'): 'center',
            'background-color': '#333',
            'box-shadow': '0 0 1.5rem rgb(255 255 255 / 33%)',
        },
    })

    button_close = button('Close')

    children = [
        button_close,
    ]

    def show(self):
        self.visible = True

    @on('keyup.esc')
    @button_close.on('click')
    def close(self, event):
        self.visible = False
        if self.on_close:
            self.on_close(False)

    def __mount__(self, element, parent, index=None):
        super().__mount__(Body.mount_element, Body)


class ModalHandler(div, content_tag=div()):
    modal: Modal

    default_style = Style()

    button_show = button('Show Modal')

    children = [
        button_show,
    ]

    @button_show.on('click')
    def show_modal(self, event):
        self.modal.show()
