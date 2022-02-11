# [PYWEB IGNORE START]
from pyweb import Tag, mount, style
from pyweb.tabs import tab, tabs
# [PYWEB IGNORE END]


class test_tabs(Tag, name='test-tabs'):
    style = style(
        color='white',
        zoom=7,
    )

    tabs = tabs(
        name='TEST',
        tabs=(
            tab(name='1', content='Test 1'),
            tab(name='2', content='Tab 2'),
        ),
    )


test = test_tabs()


mount(
    test,
    '#pyweb',
)
