from beepy import Style, Tag, attr, on
from beepy.tags import Head, p
from beepy.utils import js
from beepy.utils.asyncio import delay
from beepy.utils.js_py import replace_url

Head.title = 'Dynamic URL'


def push_hash(new_hash):
    url = js.URL.new(js.location.href)
    url.hash = new_hash

    replace_url(url, new_hash=new_hash)


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
    async def go(self):
        current_hash = js.location.hash[1:]
        for i in range(len(current_hash) + 1, -1, -1):
            push_hash(current_hash[:i] + emojis['break'] + emojis['worker'])
            await delay(100)

        for i in range(len(self.url)):
            push_hash(self.url[:i] + emojis['build'] + emojis['worker'])
            await delay(100)

        push_hash(self.url)


class DynamicURL(Tag, name='div'):
    style = Style(
        font_size='48px',
    )

    children = [Item(name, url=url) for url, name in urls.items()]
