from beepy import SpecialChild, Style
from beepy.modules.modal import Modal, ModalHandler
from beepy.tags import Head, p

Head.title = 'Modal example'


class ModalExample(Modal):
    children = [
        p('Click button below or Esc to close modal window'),
        p('Some text'),
        p('Lorem ipsum dolor sit amet, consectetur adipisicing elit.'),
        p('Nobis deserunt corrupti, ut fugit magni qui quasi nisi amet repellendus non fuga omnis'),
        p('a sed impedit explicabo accusantium nihil doloremque consequuntur.'),
        SpecialChild.SUPER,
    ]


class View(ModalHandler):
    style = Style(
        font_size='48px',
    )

    children = [
        modal := ModalExample(),
    ]
