from beepy import Tag, mount, on, state


class IncrementButton(Tag, name='button'):
    count = state(0)

    @on
    def click(self):
        self.count += 1

    def content(self):
        return f'Count: {self.count}'


mount(IncrementButton(), '#demo-getting-started')
