from pyweb import Tag, Style, CONTENT, state, mount
from pyweb.tags import button, _input


class TextSyncExample(Tag, name='example'):
    style = Style(
        zoom=5,
        input=dict(
            backgroundColor='rgb(243, 244, 246)',  # TODO: create pyweb.style.rgb function
            outline='2px solid transparent',
            padding='0.5rem 0',
        ),
    )

    value = state('')

    clear_btn = button('Clear')
    input = _input(value=value)

    children = [
        clear_btn,
        '\n',
        input,
        CONTENT,
    ]

    def content(self):
        return f'Value: {self.value}'

    @clear_btn.on('click')
    def clear(self, _event):
        self.value = ''


if __name__ == '__pyweb_root__' or __name__ == '__main__':
    mount(TextSyncExample(), '#root')
