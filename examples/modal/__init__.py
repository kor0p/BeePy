from pyweb import mount
from pyweb.style import style
from pyweb.tags import p
from pyweb.modal import Modal, ModalHandler


class TestModal(Modal):
    children = [
        p('Click button below or Esc to close modal window'),
        p('Some text'),
        p('Lorem ipsum dolor sit amet, consectetur adipisicing elit.'),
        p('Nobis deserunt corrupti, ut fugit magni qui quasi nisi amet repellendus non fuga omnis'),
        p('a sed impedit explicabo accusantium nihil doloremque consequuntur.'),
        '__SUPER__',
    ]


class Test(ModalHandler):
    style = style(
        font_size='48px',
    )

    modal = TestModal()

    children = [
        modal,
    ]


mount(
    Test(),
    '#pyweb',
)
