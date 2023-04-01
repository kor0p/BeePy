from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pyweb import Tag, Style, state
from pyweb.tags import a, p
from pyweb.utils import Interval
from pyweb.types import safe_html


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class DateTimeDisplay(Tag, name='date-time-display'):
    parent: CountUpTimer

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
        self.__render__()


class App(Tag, name='app', content_tag=p()):
    timer = CountUpTimer(start=datetime(2022, 2, 24, 3, 40, 0))

    _content = 'The full-scale invasion of Ukraine has been going on for'

    children = [
        timer,
    ]

    def mount(self):
        Style.import_file('timer.css')


if __name__ == '__pyweb_root__' or __name__ == '__main__':
    from pyweb import mount
    mount(App(), '#root')
