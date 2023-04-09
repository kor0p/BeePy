from pyweb import Style, SUPER
from pyweb.tags import p, Head
from pyweb.modal import Modal, ModalHandler


class TestModal(Modal):
    children = [
        p('Click button below or Esc to close modal window'),
        p('Some text'),
        p('Lorem ipsum dolor sit amet, consectetur adipisicing elit.'),
        p('Nobis deserunt corrupti, ut fugit magni qui quasi nisi amet repellendus non fuga omnis'),
        p('a sed impedit explicabo accusantium nihil doloremque consequuntur.'),
        SUPER,
    ]


class Test(ModalHandler):
    style = Style(
        font_size='48px',
    )

    modal = TestModal()

    children = [
        modal,
    ]

    def mount(self):
        Head.title = 'Modal example'
