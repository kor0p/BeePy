from beepy import Tag, mount, state


class Increment(Tag, name='div'):
    count = state(0, model='change')

    def content(self):
        return f'Count: {self.count}'


class View(Tag, name='view'):
    count = state(0)

    children = [
        btn_1 := Increment(count=count),
        btn_2 := Increment(count=count),
    ]

    @btn_1.on
    @btn_2.on
    def click(self):
        self.count += 1


mount(View(), '#ex-synced-counters')
