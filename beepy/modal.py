from typing import Callable

from beepy.framework import Tag, attr, state, on
from beepy.style import Style
from beepy.tags import div, button, Body


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
            'box-shadow': '0 0 1.5rem rgb(255 255 255 / 33%)',  # TODO: create beepy.style.rgb function
        },
    })

    children = [
        button_close := button('Close'),
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

    def __unmount__(self, element, parent, _unsafe=False):
        return super().__unmount__(element, parent, _unsafe=True)


class ModalHandler(div, content_tag=div()):
    modal: Modal

    default_style = Style()

    children = [
        button_show := button('Show Modal'),
    ]

    @button_show.on('click')
    def show_modal(self, event):
        self.modal.show()
