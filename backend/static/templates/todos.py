from __future__ import annotations

from beepy import Children, attr, import_css, on, state
from beepy.modules.local_storage import LocalStorage
from beepy.tags import Head, button, form, input_, li, p, span, ul

Head.title = 'Todo List'
import_css('styles/todos.css')


class TodoList(ul, content_tag=p()):
    class Todo(li, content_tag=p()):
        completed = attr(default=False)

        parent: TodoList

        children = [
            remove := span('×'),  # noqa: RUF001 - multiplication sign :)
        ]

        @on('click')
        def toggle(self):
            self.completed = not self.completed
            self.parent.sync_to_local_storage()

        @remove.on('click')
        def delete(self):
            self.parent.todos.remove(self)

    ####

    count_completed = state(0)
    class_ = 'todos'

    children = [
        add := form(
            input=input_(),
            btn=button('+', type='submit'),
        ),
        todos := Children([Todo('Create Todo List', completed=True)]),
    ]

    local_storage = LocalStorage('todos-')

    def mount(self):
        if saved_todos := self.local_storage.get('list'):
            self.todos[:] = [self.Todo(todo['text'], completed=todo['completed']) for todo in saved_todos]
        self.recalculate_completed()

    def content(self):
        return f'Completed: {self.count_completed}/{len(self.todos)}'

    @todos.onchange
    def sync_to_local_storage(self):
        self.local_storage['list'] = [{'text': todo._content[0], 'completed': todo.completed} for todo in self.todos]
        self.recalculate_completed()

    @on('submit.prevent')
    def save_todo(self):
        todo_text = self.add.input.value
        if not todo_text:
            return

        self.todos.append(self.Todo(todo_text))
        self.add.input.clear()

    def recalculate_completed(self):
        self.count_completed = len([todo for todo in self.todos if todo.completed])
