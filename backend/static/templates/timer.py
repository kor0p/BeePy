from __future__ import annotations

from datetime import UTC, datetime, timedelta

from beepy import Tag, import_css, state
from beepy.tags import a, p
from beepy.types import safe_html_content
from beepy.utils.js_py import Interval

import_css('styles/timer.css')
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class DateTimeDisplay(Tag, name='date-time-display'):
    parent: CountUpTimer

    type = state(
        type=str,
        enum=('days', 'hours', 'minutes', 'seconds'),
    )

    @safe_html_content
    def content(self):
        return f'''
<p>{self.parent[self.type]}</p>
<span>{self.type}</span>
'''


class CountUpTimer(Tag, name='timer', children_tag=a()):
    __slots__ = ('_interval',)

    start = state(_EPOCH)

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
                days=self.days, hours=self.hours, minutes=self.minutes, seconds=self.seconds
            )
        self.timer()
        self._interval = Interval(self.timer, period=1)

    def unmount(self):
        self._interval.clear()

    def timer(self):
        td = datetime.now(tz=UTC) - self.start
        dt = _EPOCH + td
        self.days = td // timedelta(days=1)
        self.hours = dt.hour
        self.minutes = dt.minute
        self.seconds = dt.second
        self.__render__()


class App(Tag, name='app', content_tag=p()):
    _content = 'The full-scale invasion of Ukraine has been going on for'

    children = [
        CountUpTimer(start=datetime(2022, 2, 24, 1, 40, 0, tzinfo=UTC)),
    ]
