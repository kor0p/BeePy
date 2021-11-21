# [PYWEB IGNORE START]
from pyweb import *
# [PYWEB IGNORE END]


class PyButton(Tag, name='button'):
    title: str = state()
    increment: int = state(1)

    @on
    def click(self, event):
        self.parent.count += self.increment

    def content(self):
        return self.title


class View(div):
    title: str = state()
    count: int = attr(0)

    button_inc = PyButton(title='+')
    button_dec = PyButton(title='-', increment=-1)

    def content(self):
        return (
            self.title,
            br,
            'Count: ', self.count
        )


mount(
    View(title='PyWeb Test 2'),
    '#pyweb',
)
