from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPException

from beepy import SpecialChild, Style, Tag, on
from beepy.attrs import html_attr, state
from beepy.modules.table import Table, TableBody, TableHead
from beepy.modules.tabs import tab, tab_title, tabs
from beepy.style import with_style
from beepy.tags import Head, button, by__ref, change, h2, label, option, select, textarea, ul
from beepy.types import AttrValue
from beepy.utils import __CONFIG__, force_sync
from beepy.utils.api import request

Head.title = 'Admin panel example'

dt_input_format = __CONFIG__['default_datetime_format'] = '%Y-%m-%dT%H:%M:%S.%fZ'
dt_view_format = '%a, %b %d %Y %X'
__CONFIG__['api_url'] = '/api/'
store = {'groups': []}


styled_button = with_style()(button)


@dataclass
class User:
    id: int | None
    username: str
    created: datetime
    group: int | None = None

    @classmethod
    def default(cls):
        return cls(id=None, username='', created=datetime.now(tz=UTC))

    def __post_init__(self):
        if isinstance(self.created, str):  # Converting to correct type
            self.created = datetime.strptime(self.created, dt_input_format).replace(tzinfo=UTC)


@dataclass
class Group:
    id: int | None
    name: str
    description: str = ''

    @classmethod
    def default(cls):
        return cls(id=None, name='')


Users = list[User]
Groups = list[Group]
users = state([], type=Users, static=True)
groups = state([], type=Groups, static=True)


@groups.on('change')
def sync_groups(_tag, value):
    store['groups'] = value


class BaseForm(Tag, name='form', content_tag=h2()):
    index = state(-1)
    visible = html_attr(default=False)

    style = Style(
        styles={
            'opacity': 0,
            'visibility': 'hidden',
            'transition': 'opacity 0.2s, visibility 0.2s',
            '&[visible]': {
                'opacity': 1,
                'visibility': 'visible',
            },
        },
    )

    children = [
        save_btn := button('Save', type='submit'),
        hide_btn := button('Cancel'),
        error := state(''),
    ]

    def show(self):
        self.visible = True

    @hide_btn.on('click')
    def hide(self):
        self.visible = False


class ViewTimestamp(AttrValue):
    def __view_value__(self):
        return self.value.strftime(dt_view_format)


class ViewGroup(AttrValue):
    def __view_value__(self):
        for group in store['groups']:
            if group.id == self.value:
                return group.name

        return self.value


class UsersTable(Table):
    head = TableHead(
        columns=[
            {'id': 'id', 'label': 'ID'},
            {'id': 'username', 'label': 'Username'},
            {'id': 'created', 'label': 'Created', 'view': ViewTimestamp},
            {'id': 'group', 'label': 'Group', 'view': ViewGroup},
        ],
    )
    body = TableBody(rows=[])


class UserForm(BaseForm):
    user = state(
        User.default(),
        type=User,
        model_options={'attribute': by__ref},
    )

    def title(self):
        if self.user and self.user.id is not None:
            return f'Edit user #{self.user.id}'
        else:
            return 'Add user'

    parent: UsersTab

    username = change(value=user)
    group = select(value=user)

    children = [
        title,
        label('Username', for_=username),
        username,
        label('Group', for_=group),
        group,
        SpecialChild.SUPER,
    ]

    @on('submit.prevent')
    async def save(self):
        try:
            if self.user.id is not None:
                user = await request(f'users/{self.user.id}', method='PUT', body=self.user)
            else:
                user = await request('users/', method='POST', body=self.user)
        except HTTPException as error:
            self.error = f'Error in request: {error}'
        else:
            self.hide()
            self.error = ''
            self.user = User.default()
            await self.parent.refresh_user(self.index, user)
        self.parent.__render__()

    @groups.on('change')
    def global_groups_change(self, _tag, value):
        user_group = self.user and self.user.group
        self.group.options[:] = [
            option(label=group.name, value=group.id, defaultSelected=group.id == user_group) for group in value
        ]


class UsersTab(tab, name='users', content_tag=h2()):
    users: Users = users

    style = Style(
        get_vars=lambda self, ref, **_: {'button_ref': ref(self.add_btn)},
        styles={
            '{button_ref}': {
                'margin': '8px',
            },
        },
    )

    children = [
        error := state(''),
        table := UsersTable(),
        add_btn := styled_button('Add User'),
        form := UserForm(),
    ]

    @add_btn.on('click')
    def add_new_user(self):
        self.form.index = -1
        self.form.user = User.default()
        self.form.show()

    @table.on(':edit')
    def edit_user(self, index, row):
        self.form.index = index
        self.form.user = User(**row)
        self.form.show()

    @table.on(':delete')
    async def delete_user(self, row):
        id = row['id']
        try:
            await request(f'users/{id}', method='DELETE')
        except HTTPException as error:
            self.error = f'Error in request: {error}'
        else:
            self.table.delete_row(id=id)
            self.error = ''

    @groups.on('change')
    def reload_groups_changed(self, _tag):
        self.table.body.sync()
        self.__render__()

    async def refresh_user(self, index, user):
        if index < 0:  # new user
            await asyncio.sleep(0.5)
            return await self.load_users()

        self.users[index] = User(**user)
        self.table.body.rows[index] = user
        self.table.body.sync()  # TODO: make .rows - TrackableList?

    async def load_users(self):
        try:
            new_users = await request('users/')
        except HTTPException as error:
            self.error = f'Error in request: {error}'
        else:
            self.users = [User(**user) for user in new_users]
            self.table.body.rows = new_users
            self.form.user = None
            self.error = ''


class GroupsTable(Table):
    head = TableHead(
        columns=[
            {'id': 'id', 'label': 'ID'},
            {'id': 'name', 'label': 'Name'},
            {'id': 'description', 'label': 'Description'},
        ],
    )
    body = TableBody(rows=[])


class GroupForm(BaseForm):
    group = state(
        Group.default(),
        type=Group,
        model_options={'attribute': by__ref},
    )

    def title(self):
        if self.group and self.group.id is not None:
            return f'Edit group #{self.group.id}'
        else:
            return 'Add group'

    parent: GroupsTab

    name = change(value=group)
    description = textarea(value=group)

    children = [
        title,
        label('Name', for_=name),
        name,
        label('Description', for_=description),
        description,
        SpecialChild.SUPER,
    ]

    @on('submit.prevent')
    async def save(self):
        try:
            if self.group.id is not None:
                group = await request(f'groups/{self.group.id}', method='PUT', body=self.group)
            else:
                group = await request('groups/', method='POST', body=self.group)
        except HTTPException as error:
            self.error = f'Error in request: {error}'
        else:
            self.hide()
            self.error = ''
            self.group = Group.default()
            await self.parent.refresh_group(self.index, group)
        self.parent.__render__()


class GroupsTab(tab, name='groups', content_tag=h2()):
    groups: Groups = groups

    style = Style(
        get_vars=lambda self, ref, **_: {'button_ref': ref(self.add_btn)},
        styles={
            '{button_ref}': {
                'margin': '8px',
            },
        },
    )

    children = [
        error := state(''),
        table := GroupsTable(),
        add_btn := styled_button('Add Group'),
        form := GroupForm(),
    ]

    @add_btn.on('click')
    def add_new_group(self):
        self.form.index = -1
        self.form.group = Group.default()
        self.form.show()

    @table.on(':edit')
    def edit_group(self, index, row):
        self.form.index = index
        self.form.group = Group(**row)
        self.form.show()

    @table.on(':delete')
    async def delete_group(self, row):
        id = row['id']
        try:
            await request(f'groups/{id}', method='DELETE')
        except HTTPException as error:
            self.error = f'Error in request: {error}'
        else:
            self.table.delete_row(id=id)
            self.error = ''

    async def refresh_group(self, index, group):
        if index < 0:  # new group
            await asyncio.sleep(0.5)
            return await self.load_groups()

        self.groups[index] = Group(**group)
        self.table.body.rows[index] = group
        self.table.body.sync()  # TODO: make .rows - TrackableList?

    async def load_groups(self):
        try:
            new_groups = await request('groups/')
        except HTTPException as error:
            self.error = f'Error in request: {error}'
        else:
            self.groups = [Group(**group) for group in new_groups]
            self.table.body.rows = new_groups
            self.form.group = None
            self.error = ''


class Admin(tabs, name='app'):
    dark_theme = True
    name = 'admin'

    children = [
        tabs_titles := ul(
            users=tab_title('Users'),
            groups=tab_title('Groups'),
        ),
        users := UsersTab(),
        groups := GroupsTab(),
    ]

    def pre_mount(self):
        self.load_data()

    @force_sync.wait_load
    async def load_data(self):
        await self.groups.load_groups()
        await self.users.load_users()
