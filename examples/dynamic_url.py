import js
from pyweb import Tag, attr, on, mount
from pyweb.tags import p, Head
from pyweb.style import style
from pyweb.utils import delay


def push_hash(hash):
    url = js.URL.new(js.location.href)
    url.hash = hash

    js.history.pushState(hash, hash, url.href)


push_hash('/')


emojis = {
    'worker': '👷',
    'build': '🏗',
    'break': '🔨',
}


urls = {
    '/': 'Index',
    '/about': 'About us',
    '/my-cool-url': 'My Cool Url',
}


class Item(Tag, name='item', content_tag=p()):
    url = attr(type=str)

    @on('click')
    async def go(self, event):
        current_hash = js.location.hash[1:]
        for i in range(len(current_hash) + 1, -1, -1):
            push_hash(current_hash[:i] + emojis['break'] + emojis['worker'])
            await delay(100)

        for i in range(len(self.url)):
            push_hash(self.url[:i] + emojis['build'] + emojis['worker'])
            await delay(100)

        push_hash(self.url)


class DynamicURL(Tag, name='div'):
    style = style(
        font_size='48px',
    )

    children = [
        Item(name, url=url)
        for url, name in urls.items()
    ]

    def mount(self):
        Head.title = 'Dynamic URL'


if __name__ == '__pyweb_root__':
    mount(DynamicURL(), '#root')