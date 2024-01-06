from beepy import Tag, mount, state, on


class IncrementButton(Tag, name='button'):
    count = state(0)

    @on
    def click(self):
        self.count += 1

    def content(self):
        return f'Count: {self.count}'


mount(IncrementButton(), '#root')
