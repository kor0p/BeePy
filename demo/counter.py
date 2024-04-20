from beepy import Tag, mount, on, state


class Increment(Tag, name='div'):
    count = state(0)

    @on
    def click(self):
        self.count += 1

    def content(self):
        return f'Count: {self.count}'


mount(Increment(), '#ex-counter')
