from __future__ import annotations

from typing import Literal, TypeVar

from beepy import Children, Style, on, state
from beepy.modules.actions import Action
from beepy.tags import table, tbody, td, th, thead, tr
from beepy.utils.asyncio import ensure_sync_many
from beepy.utils.common import call_handler_with_optional_arguments

T = TypeVar('T')


class TableCellAction(Action, _root=True):
    components: dict[str, type[TableCellAction]] = {}

    parent: TD

    @on
    def click(self, event):
        tr: TR = self.parent.parent
        table: Table = tr.parent.parent
        row = table._map_data(tr.raw_data)
        index = table.find_row_index(id=row['id'])

        ensure_sync_many(
            [
                call_handler_with_optional_arguments(
                    handler, table.parent, {'event': event, 'action': self.action_name, 'index': index}, row
                )
                for handler in table._handlers[self.action_name]
            ],
            lambda *_: table.parent.__render__(),
        )


class ActionEdit(TableCellAction):
    action_name = 'edit'
    _content = 'Edit'


class ActionDelete(TableCellAction):
    action_name = 'delete'
    _content = 'Delete'


class TH(th):
    parent: TR


class TD(td):
    parent: TR


class TR(tr):
    data = state(type=list[dict[str, str]])

    parent: TableHead | TableBody

    children = [
        _data := Children(),  # TODO: add auto-reload data, instead of `sync` functions
    ]

    @property
    def raw_data(self):
        return [line['value'] for line in self.data if isinstance(line, dict)]

    @property
    def view_data(self):
        return [(line['view'] if isinstance(line, dict) else line) for line in self.data]

    @data.on('mount', 'change')
    def sync(self):
        self._data[:] = [(TD(str(line['view'])) if isinstance(line, dict) else TD(*line)) for line in self.data]


class TableHead(thead, children_tag=TR(), force_ref=True):
    columns = state(type=list[dict[Literal['id', 'label', 'view'], str]])
    # TODO: maybe use 'name' instead of 'id'
    #       add 'hidden' option (availability to hide some columns)

    parent: Table

    children = [
        _columns := Children(),
    ]

    @columns.on('mount', 'change')
    def sync(self):
        if self._parent_ is None:
            return

        self._columns[:] = [TH(column['label']) for column in self.columns]
        if self.parent.actions:
            self._columns.append(TH('Actions'))


class TableBody(tbody, force_ref=True):
    rows = state(type=list[list[str]])

    parent: Table

    children = [
        _rows := Children(),
    ]

    @rows.on('mount', 'change')
    def sync(self):
        if self._parent_ is None:
            return

        self._rows[:] = [
            TR(
                data=[
                    *(
                        {'value': cell, 'view': col['view'](cell).__view_value__() if 'view' in col else cell}
                        for col, cell in self.parent._zip_column_row(row)
                    ),
                    [TableCellAction.components[action]() for action in self.parent.actions],
                ],
            )
            for row in self.rows
        ]

    def delete_row(self, index):
        self.rows.pop(index)
        self._rows.pop(index)


class Table(table):
    actions = ('edit', 'delete')

    head: TableHead
    body: TableBody

    default_style = Style(
        styles={
            '&': {
                'border-spacing': 0,
                'border-collapse': 'collapse',
            },
            '& >': {
                '&, th, td': {
                    'border': '1px solid #333',
                },
                'th, td': {
                    'padding': '8px',
                },
            },
        },
    )

    def _zip_column_row(self, row):
        if isinstance(row, dict):
            for col in self.head.columns:
                yield col, row[col['id']]
        else:
            for index, col in enumerate(self.head.columns):
                yield col, row[index]

    def _map_data(self, row):
        if isinstance(row, dict):
            return row
        return dict(zip([col['id'] for col in self.head.columns], row, strict=True))

    @property
    def data(self):
        return [self._map_data(row) for row in self.body.rows]

    def find_row_index(self, *, raise_key_error=True, **filters):
        if '_index' in filters:
            return filters['_index']

        row_index = None

        for index, row in enumerate(self.data):
            for key, value in filters.items():
                if row[key] == value:
                    row_index = index
                    break
            else:
                continue
            break

        if raise_key_error and row_index is None:
            raise KeyError(str(filters))

        return row_index

    def find_row(self, **filters):
        return self.body.rows[self.find_row_index(**filters)]

    def delete_row(self, **filters):
        self.body.delete_row(self.find_row_index(**filters))
