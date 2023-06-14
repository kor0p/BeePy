from __future__ import annotations

from beepy import Style, attr, state, on
from beepy.tags import p, _input, button, span, ul, li, form, Head
from beepy.children import Children
from beepy.local_storage import LocalStorage


Head.title = 'Todo List'
Style.import_file('styles/todos.css')


class TodoList(ul, content_tag=p()):
    class Todo(li, content_tag=p()):
        completed = attr(False)

        parent: TodoList

        remove = span('×')

        children = [
            remove,
        ]

        @on('click')
        def toggle(self, event):
            self.completed = not self.completed
            self.parent.sync_to_local_storage()

        @remove.on('click')
        def delete(self, event):
            self.parent.todos.remove(self)

    ####

    count_completed = state(0)
    class_ = 'todos'

    todos = Children([
        Todo('Create Todo List', completed=True),
    ])
    add = form(
        input=_input(),
        btn=button('+', type='submit'),
    )

    children = [
        add,
        todos,
    ]

    local_storage = LocalStorage('todos-')

    def mount(self):
        if (saved_todos := self.local_storage.get('list')):
            self.todos[:] = [
                self.Todo(todo['text'], completed=todo['completed'])
                for todo in saved_todos
            ]
        self.recalculate_completed()

    def content(self):
        return f'Completed: {self.count_completed}/{len(self.todos)}'

    @todos.onchange
    def sync_to_local_storage(self):
        self.local_storage['list'] = [
            {'text': todo._content[0], 'completed': todo.completed}
            for todo in self.todos
        ]
        self.recalculate_completed()

    @on('submit.prevent')
    def save_todo(self, event):
        todo_text = self.add.input.value
        if not todo_text:
            return

        self.todos.append(self.Todo(todo_text))
        self.add.input.clear()

    def recalculate_completed(self):
        self.count_completed = len([todo for todo in self.todos if todo.completed])
