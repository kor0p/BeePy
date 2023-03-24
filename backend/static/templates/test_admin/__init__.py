from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from pyweb import Tag, Style, SUPER, on, mount
from pyweb.style import with_style
from pyweb.attrs import attr, state
from pyweb.tags import button, by__input_id, _input, textarea, option, select, h2, label
from pyweb.tabs import tabs, tab, tab_title
from pyweb.table import Table, TableHead, TableBody
from pyweb.types import AttrValue
from pyweb.utils import __CONFIG__, request, ensure_sync


dt_input_format = __CONFIG__['default_datetime_format'] = '%Y-%m-%dT%H:%M:%S.%fZ'
dt_view_format = '%a, %b %d %Y %X'
store = {'groups': []}


@dataclass
class User:
    id: Optional[int]
    username: str
    created: datetime
    group: Optional[int] = None

    @classmethod
    def default(cls):
        return cls(id=None, username='', created=datetime.now())


@dataclass
class Group:
    id: Optional[int]
    name: str
    description: str = ''

    @classmethod
    def default(cls):
        return cls(id=None, name='')


Users = list[User, ...]
Groups = list[Group, ...]
users = state([], type=Users, static=True)
groups = state([], type=Groups, static=True)


@groups.on('change')
def sync_groups(__from_tag, new_groups):
    store['groups'] = new_groups


class BaseForm(Tag, name='form', content_tag=h2()):
    error = state('')
    visible = attr(False)

    style = Style(styles={
        'opacity': 0,
        'visibility': 'hidden',
        'transition': 'opacity 0.2s, visibility 0.2s',
        '&[visible]': {
            'opacity': 1,
            'visibility': 'visible',
        },
    })

    save_btn = button('Save', type='submit')

    children = [
        save_btn,
        error,
    ]

    def show(self):
        self.visible = True

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
    head = TableHead(columns=[
        dict(id='id', label='ID'),
        dict(id='username', label='Username'),
        dict(id='created', label='Created', view=ViewTimestamp),
        dict(id='group', label='Group', view=ViewGroup),
    ])
    body = TableBody(rows=[])


class UserForm(BaseForm):
    user = state(
        User.default(),
        type=User,
        model_options={'attribute': by__input_id},
    )

    def title(self):
        if self.user and self.user.id is not None:
            return f'Edit user #{self.user.id}'
        else:
            return 'Add user'

    parent: UsersTab

    username = _input(value=user)
    group = select(value=user)

    children = [
        title,
        label('Username', _for=username),
        username,
        label('Group', _for=group),
        group,
        SUPER,
    ]

    @on('submit.prevent')
    async def save(self, event):
        try:
            if self.user.id is not None:
                await request(f'users/{self.user.id}', method='PUT', body=self.user)
            else:
                await request('users/', method='POST', body=self.user)
        except Exception as error:
            self.error = f'Error in request: {error}'
        else:
            self.error = ''
            self.user = User.default()
            self.hide()
            await self.parent.load_users()
        self.parent.__render__()

    @groups.on('change')
    def global_groups_change(self, __tag, new_groups):
        user_group = self.user and self.user.group
        self.group.options[:] = [
            option(
                label=group.name,
                value=group.id,
                defaultSelected=group.id == user_group
            ) for group in new_groups
        ]


class UsersTab(tab, name='users'):
    error = state('')
    users: Users = users

    style = Style(styles={
        '{ref(add_btn)}': {
            'margin': '8px',
        },
    })

    table = UsersTable()
    add_btn = with_style()(button)('Add User')
    form = UserForm()

    children = [
        error,
        table,
        add_btn,
        form,
    ]

    @add_btn.on('click')
    def add_new_user(self, event):
        self.form.user = User.default()
        self.form.show()

    @table.on(':edit')
    def edit_user(self, event, _action, row):
        self.form.user = User(**row)
        self.form.show()

    @table.on(':delete')
    def delete_user(self, event, _action, row):
        # TODO: request to DELETE user on backend
        self.table.delete_row(id=row['id'])

    def mount(self):
        ensure_sync(self.load_users())

    async def load_users(self):
        try:
            new_users = await request('users/')
        except Exception as error:
            self.error = f'Error in request: {error}'
        else:
            new_users = [{
                **user,
                'created': datetime.strptime(user['created'], dt_input_format)
            } for user in new_users]
            self.users = [User(**user) for user in new_users]
            self.table.body.rows = new_users
            self.form.user = None
            self.error = ''


class GroupsTable(Table):
    head = TableHead(columns=[
        dict(id='id', label='ID'),
        dict(id='name', label='Name'),
        dict(id='description', label='Description'),
    ])
    body = TableBody(rows=[])


class GroupForm(BaseForm):
    group = state(
        Group.default(),
        type=Group,
        model_options={'attribute': by__input_id},
    )

    def title(self):
        if self.group and self.group.id is not None:
            return f'Edit group #{self.group.id}'
        else:
            return 'Add group'

    parent: GroupsTab

    name = _input(value=group)
    description = textarea(value=group)

    children = [
        title,
        label('Name', _for=name),
        name,
        label('Description', _for=description),
        description,
        SUPER,
    ]

    @on('submit.prevent')
    async def save(self, event):
        try:
            if self.group.id is not None:
                await request(f'groups/{self.group.id}', method='PUT', body=self.group)
            else:
                await request('groups/', method='POST', body=self.group)
        except Exception as error:
            self.error = f'Error in request: {error}'
        else:
            self.error = ''
            self.group = Group.default()
            self.hide()
            await self.parent.load_groups()  # TODO: add add_row method for table
        self.parent.__render__()


class GroupsTab(tab, name='groups'):
    error = state('')
    groups: Groups = groups

    style = Style(styles={
        '{ref(add_btn)}': {
            'margin': '8px',
        },
    })

    table = GroupsTable()
    add_btn = with_style()(button)('Add Group')
    form = GroupForm()

    children = [
        error,
        table,
        add_btn,
        form,
    ]

    @add_btn.on('click')
    def add_new_group(self, event):
        self.form.group = Group.default()
        self.form.show()

    @table.on(':edit')
    def edit_group(self, event, _action, row):
        self.form.group = Group(**row)
        self.form.show()

    @table.on(':delete')
    def delete_group(self, event, _action, row):
        # TODO: request to DELETE group on backend
        self.table.delete_row(id=row['id'])

    def mount(self):
        ensure_sync(self.load_groups())

    async def load_groups(self):
        try:
            new_groups = await request('groups/')
        except Exception as error:
            self.error = f'Error in request: {error}'
        else:
            self.groups = [Group(**group) for group in new_groups]
            self.table.body.rows = new_groups
            self.form.group = None
            self.error = ''


class Admin(tabs, name='app'):
    name = 'admin'

    tabs_titles = {
        'users': tab_title('Users'),
        'groups': tab_title('Groups'),
    }

    users = UsersTab()
    groups = GroupsTab()

    # TODO: create some `async def load()` instead of this
    ensure_sync(groups.load_groups())
    ensure_sync(users.load_users())

    children = [
        users,
        groups,
    ]


mount(
    Admin(),
    '#root',
)
