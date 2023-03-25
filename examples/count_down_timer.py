from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pyweb import Tag, Style, state
from pyweb.tags import a, p
from pyweb.utils import Interval
from pyweb.types import safe_html


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class DateTimeDisplay(Tag, name='div'):
    parent: CountUpTimer

    style = Style(styles={
        '> div': {
            'line-height': '2.5rem',
            'padding': '0 0.75rem 0 0.75rem',
            'align-items': 'center',
            'display': 'flex',
            'flex-direction': 'column',

            '> p': {
                'margin': 0,
            },
            '> span': {
                'text-transform': 'uppercase',
                'font-size': '1.5rem',
                'line-height': '2rem',
            },
        },
    })

    type = state(
        type=str,
        enum=('days', 'hours', 'minutes', 'seconds'),
    )

    @safe_html.content
    def content(self):
        return f'''
<p>{self.parent[self.type]}</p>
<span>{self.type}</span>
'''


class CountUpTimer(Tag, name='timer', children_tag=a()):
    __slots__ = ('_interval',)

    style = Style(styles={
        'padding': '0.5rem',

        '> a': {
            'display': 'flex',
            'flex-direction': 'row',
            'justify-content': 'center',
            'align-items': 'center',
            'font-weight': 700,
            'font-size': '2rem',
            'line-height': '3.5rem',
            'padding': '0.5rem',
            'border': '1px solid #ebebeb',
            'border-radius': '0.25rem',
            'text-decoration': 'none',
        },
    })

    start = state(_EPOCH)
    _value = state(0, notify=True)

    days = state(0)
    hours = state(0)
    minutes = state(0)
    seconds = state(0)

    children = [
        DateTimeDisplay(type='days'),
        p(':'),
        DateTimeDisplay(type='hours'),
        p(':'),
        DateTimeDisplay(type='minutes'),
        p(':'),
        DateTimeDisplay(type='seconds'),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interval = None

    def mount(self):
        if self.start == _EPOCH:
            self.start = _EPOCH + timedelta(
                days=self.days, hours=self.hours, minutes=self.minutes, seconds=self.seconds,
            )
        self.timer()
        self._interval = Interval(self.timer, period=1)

    def unmount(self):
        self._interval.clear()

    def timer(self):
        td = datetime.now() - self.start
        dt = _EPOCH + td
        self.days = td // timedelta(days=1)
        self.hours = dt.hour
        self.minutes = dt.minute
        self.seconds = dt.second
        self._value = dt.timestamp()  # notify=True will re-render current element


class App(Tag, name='div', content_tag=p()):
    style = Style(styles={
        '> p': {
            'display': 'flex',
            'flex-direction': 'row',
            'justify-content': 'center',
            'align-items': 'center',
            'font-size': '2rem',
        },
    })

    timer = CountUpTimer(start=datetime(2022, 2, 24, 3, 40, 0))

    _content = 'The full-scale invasion of Ukraine has been going on for'

    children = [
        timer,
    ]


if __name__ == '__pyweb_root__' or __name__ == '__main__':
    from pyweb import mount
    mount(App(), '#root')
