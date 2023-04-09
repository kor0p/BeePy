from __future__ import annotations

from pyweb import Tag, Style, attr, state, on
from pyweb.tags import div, p, _input, button, span, Head
from pyweb.children import Children
from pyweb.local_storage import LocalStorage


class TodoList(Tag, name='ul'):
    class AddTodo(div, name='form'):
        input = _input()
        button = button('+', type='submit')

        children = [
            input,
            button,
        ]

        parent: TodoList

        @on('submit.prevent')
        def save_todo(self, event):
            self.parent.add_todo(self.input.value)
            self.input.clear()

    ####

    class Todo(Tag, name='li', content_tag=p()):
        completed = attr(False)

        parent: TodoList

        remove = span('×')

        children = [
            remove,
        ]

        @on('click')
        def toggle(self, event):
            self.completed = not self.completed
            self.parent.recalculate_completed()

        @remove.on('click')
        def delete(self, event):
            self.parent.todos.remove(self)

    ####

    count_completed = state(0)

    style = Style(styles={
        'zoom': 3,
        'padding': '0 24px',
        'form': {
            'display': 'flex',
            'flex-flow': 'row nowrap',
            'align-items': 'center',
            'input': {
                'border': 'none',
                'outline': 'none',
                'border-radius': '.5rem',
                'padding': '.5rem',
                'height': '1.5rem',
                'flex': '0 1 calc(90% - 0.5rem)',
                'margin-right': '.5rem',
            },
            'button': {
                'cursor': 'pointer',
                'height': '2.5rem',
                'width': '2.5rem',
                'border-radius': '.5rem',
                'font-size': '1.25rem',
                'font-weight': 500,
                'border': 'none',
                'outline': 'none',
                'color': '#dddddd',
                'background-color': '#4a8cce',
            },
        },
        'li': {
            'display': 'flex',
            'flex-flow': 'row nowrap',
            'align-items': 'center',
            'user-select': 'none',
            'span': {
                'cursor': 'pointer',
                'margin-right': '1rem',
                '&:hover': {
                    'color': '#f05454',
                }
            },
            '&[completed]': {
                'p:before': {
                    'top': '10px',
                    'height': '2px',
                    'transform': 'scaleX(1)',
                },
            },
            'p': {
                'cursor': 'pointer',
                'position': 'relative',
                'margin-right': '1rem',
                '&:before': {
                    'position': 'absolute',
                    'z-index': 5,
                    'content': '',
                    'top': '9px',
                    'left': 0,
                    'width': '100%',
                    'height': '4px',
                    'background-color': '#4a8cce',
                    'transform': 'scaleX(0)',
                    'transform-origin': 'left',
                    'transition': 'all .2s ease-in-out',
                },
                '&:hover:before': {
                    'top': '9px',
                    'height': '4px',
                    'transform': 'scaleX(1)',
                },
            },
        },
    })

    add = AddTodo()

    todos = Children([
        Todo('Create Todo List', completed=True),
    ])

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
        Head.title = 'Todo List'

    def content(self):
        return f'Completed: {self.count_completed}/{len(self.todos)}'

    @todos.onchange
    def sync_to_local_storage(self):
        self.local_storage['list'] = [
            {'text': todo._content[0], 'completed': todo.completed}
            for todo in self.todos
        ]

    def add_todo(self, todo_text):
        if not todo_text:
            return

        self.todos.append(self.Todo(todo_text))

    def recalculate_completed(self):
        self.sync_to_local_storage()
        self.count_completed = len([todo for todo in self.todos if todo.completed])
