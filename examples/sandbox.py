from beepy import Head, Style, Tag, empty_tag, mount, state
from beepy.tags import button, div, p, textarea
from beepy.types import safe_html
from beepy.utils import ensure_sync, js

Head.title = 'Sandbox'


DEMO_CODE = safe_html(
    '''from beepy import Tag, state, on

class Main(Tag, name='button'):
    count = state(0)

    @on
    def click(self):
        self.count += 1

    def content(self):
        return f'Count: {self.count}'
'''
)
DEMO_MOUNT_CODE = '''
from beepy import mount
mount(Main(), '#demo', clear=True)
'''

pre = empty_tag('pre')


class View(Tag, name='view'):
    style = Style(
        zoom=2,
        button={
            'display': 'block',
            'margin': '4px',
        },
        textarea={
            'height': '300px',
            'width': '400px',
        },
    )

    children = [
        btn := button('Run'),
        reset := button('Reset'),
        input := textarea(value=DEMO_CODE, data_gramm=False),
        p('Main is mounted by this code: '),
        pre(DEMO_MOUNT_CODE),
        div(id='demo'),
        error := state(''),
    ]

    @btn.on('click')
    async def run(self):
        self.error = ''
        try:
            await js.apy(self.input.value + '\n\n' + DEMO_MOUNT_CODE)
        except Exception as e:  # noqa: BLE001 - catching any bad user input :)
            self.error = str(e)

    @reset.on('click')
    def reset_to_demo(self):
        self.input.value = DEMO_CODE

    def mount(self):
        ensure_sync(self.run())


mount(View(), '#root')
