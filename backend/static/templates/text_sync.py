from beepy import SpecialChild, Style, Tag, state
from beepy.tags import button, input_


class TextSyncExample(Tag, name='example'):
    style = Style(
        zoom=5,
        input={
            'outline': '2px solid transparent',
            'padding': '0.5rem 0',
        },
    )

    value = state('')

    children = [
        clear_btn := button('Clear'),
        '\n',
        input := input_(value=value),
        SpecialChild.CONTENT,
    ]

    def content(self):
        return f'Value: {self.value}'

    @clear_btn.on('click')
    def clear(self):
        self.value = ''
