import re
from collections.abc import Iterable
from typing import Any, Protocol

from beepy.attrs import attr, state
from beepy.context import Context
from beepy.framework import Tag, __config__
from beepy.tags import Head
from beepy.types import AttrValue, safe_html, safe_html_content
from beepy.utils import js
from beepy.utils.common import MISSING, get_random_name, log10_ceil, safe_issubclass, to_kebab_case


def dict_of_properties_to_css(properties):
    for prop, value in properties.items():
        if not prop:
            yield value
            continue
        if not isinstance(prop, Iterable) or isinstance(prop, str):
            prop = (prop,)  # noqa: PLW2901
        if value == '':
            value = '""'  # noqa: PLW2901
        result = ''
        for _property in prop:
            _property = to_kebab_case(_property)
            result += '    ' + _property
            if isinstance(value, tuple | list):  # handle raw css
                result += ' ' + (_property + ' ').join(x for x in value if x)
            else:
                result += f': {value};'
        yield result


def dict_of_parents_to_css(children, parent, braces):
    for child, value in children.items():
        if not child:
            yield f' {braces[0]} {child.strip()} {braces[1]}'
        if isinstance(child, tuple | set):
            child = ','.join(child)  # noqa: PLW2901
        child = re.sub('&', parent, child) if '&' in child else parent + ' ' + child  # noqa: PLW2901
        for inner in dict_to_css_iter(value, child, braces):
            if child.startswith('@') and not parent:
                yield f' {braces[0]} {inner.strip()} {braces[1]}'
            else:
                yield inner


def dict_to_css_iter(selectors: dict, parent: str = '', braces=('{', '}')):
    """
    parses nested dict to css

    dict(
        div=dict(
            color='red',
            backgroundColor='blue',
            p={
                'font-size': '20px',
                '&.class': dict(
                    font_size='30px',
                ),
                '': '''
                    // some raw css
                '''
            }
        )
    )

    to

    div {
        color: red;
        background-color: blue;
    }
    div p {
        font-size: 20px;
                    // some raw css
    }
    div p.class {
        font-size: 30px;
    }


    """

    # TODO: implement all scss or create wheel of libsass, add micropip.import and refactor styles

    children = {}
    properties = {}

    for prop, value in selectors.items():
        if isinstance(value, dict):
            children[prop] = value
        else:
            properties[prop] = value

    if properties:
        yield parent + ' ' + braces[0]
        yield from dict_of_properties_to_css(properties)
        yield braces[1]

    yield from dict_of_parents_to_css(children, parent, braces)


def dict_to_css(*args, separator='\n', **kwargs):
    return separator.join(dict_to_css_iter(*args, **kwargs))


def get_reference(tag: Tag):
    return f'[style-id="{tag.style_id}"]'


class Var:
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f'var(--{self.name})'


class StyleRef(AttrValue):
    __slots__ = ('vars', '_style')

    def __init__(self, style_id, style):
        super().__init__(style_id)
        self.vars = {}
        self._style = style

    def __repr__(self):
        return self.value

    __view_value__ = __repr__


class Raw:
    def __bool__(self):
        return False


class TagWithStyle(Protocol):
    style_id: StyleRef


class Style(Tag, name='style', content_tag=None, raw_html=True, force_ref=True):
    __slots__ = ('styles', '_main_style', 'real_parent')

    __extra_attributes__ = {
        'style_id': attr(type=StyleRef),
    }

    _global = {
        'styles_count': 1,
    }

    options = state(type=dict)
    real_parent: Tag | TagWithStyle | None  # Actually it's only `Tag`;   `TagWithStyle` is used only for type checking

    @classmethod
    def from_css(cls, _file):
        # TODO: implement converting from css/scss/pycss to Style
        raise NotImplementedError('TBD...')

    def __init__(self, styles=None, options=None, get_vars=None, **styles_dict):
        super().__init__()
        if styles and not styles_dict:
            styles_dict = styles
        if options is None:
            options = {}
        self.styles = styles_dict
        self._content = ''
        self._main_style = False
        self.real_parent = None
        self.options = {
            'global': False,
            'render_states': True,
            'render_children': True,
            'get_vars_callback': get_vars,
        } | options

    def _mount_(self, element, parent, index=None):
        self.real_parent = parent
        if __config__['style_head']:
            super()._mount_(Head.mount_element, Head)
        else:
            super()._mount_(element, parent, index)

    def _unmount_(self, element, parent, *, _unsafe=False):
        return super()._unmount_(element, parent, _unsafe=True)

    def mount(self):
        styles = {Raw(): '{__VARS__}'} | self.styles
        parent = self.real_parent

        if self.options['global']:  # TODO: add example
            self._content = dict_to_css(styles, parent._tag_name_)
            return

        if parent.style_id is None:  # support multiple style children
            self._global['styles_count'] += 1
            style_id = get_random_name(log10_ceil(self._global['styles_count']) + 1)
            parent.style_id = StyleRef(style_id, self)
            self._main_style = True
        else:
            style_id = parent.style_id

        # TODO: is [style-id=] slow? If so, maybe use classes?
        self._content = dict_to_css(styles, f'{parent._tag_name_}[style-id="{style_id}"]', braces=('{{', '}}'))

    @safe_html_content
    def content(self):
        if self.options['global'] or not self._content:
            return self._content

        parent = self.real_parent
        params: dict[str, Any] = {'__VARS__': ''}

        if self.options['render_states']:
            params.update(parent._states)

        if self.options['render_children']:
            params.update(parent.ref_children)

        if get_vars := self.options['get_vars_callback']:
            params.update(get_vars(self=parent, ref=get_reference, **params))

        if self._main_style and (vars := parent.style_id.vars):
            # TODO: add mangling for --var names
            params['__VARS__'] = dict_to_css({safe_html(f'--{name}'): var for name, var in vars.items()}).strip()[1:-1]

        # TODO: use native css '--var: {}' instead of re-render the whole content
        return self._content.strip().format(**params)

    def var(self, name, new_value=MISSING):
        parent = self.real_parent
        if not parent:
            return

        if new_value is MISSING:
            return parent.style_id.vars[name]

        if new_value is None:
            del parent.style_id.vars[name]
        else:
            parent.style_id.vars[name] = new_value
        if parent._mount_finished_:
            parent.__render__()


def import_css(file_path):
    return js.beepy.addElement(
        js.document.head,
        'link',
        href=js.beepy.files.getPathWithCurrentPathAndOrigin(file_path),
        onload=Context.create_onload(),
        type='text/css',
        rel='stylesheet',
    )


def with_style(style_or_tag_cls: Style | type[Tag] | None = None):
    """
    @with_style
    class Button(Tag, name='button'):
        ...

    styled_button = with_style(Style(display='block', **kwargs))(button)
    """

    def wrapper(tag_cls: type[Tag]):
        return type(tag_cls.__name__, (tag_cls,), {'style': style_or_tag_cls or Style()})

    if safe_issubclass(style_or_tag_cls, Tag):
        _tag_cls, style_or_tag_cls = style_or_tag_cls, None
        return wrapper(_tag_cls)

    return wrapper


__all__ = ['Style', 'import_css', 'with_style', 'dict_to_css_iter', 'dict_to_css']
