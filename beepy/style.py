import re
from typing import Any, Optional, Type

from beepy.framework import __CONFIG__, Tag, attr, state
from beepy.utils import js
from beepy.utils.common import log10_ceil, get_random_name, to_kebab_case, safe_issubclass
from beepy.tags import Head
from beepy.types import safe_html


def dict_of_properties_to_css(properties):
    for prop, value in properties.items():
        if not prop:
            yield value
            continue
        if not isinstance(prop, (tuple, set)):
            prop = (prop,)
        result = ''
        for _property in prop:
            _property = to_kebab_case(_property)
            result += '    ' + _property
            if isinstance(value, (list, tuple)):  # handle raw css
                result += ' ' + (_property + ' ').join(x for x in value if x)
            else:
                if value == '':
                    value = '""'
                result += f': {value};'
        yield result


def dict_of_parents_to_css(children, parent, braces):
    for child, value in children.items():
        if not child:
            yield f' {braces[0]} {child.strip()} {braces[1]}'
        if isinstance(child, (tuple, set)):
            child = ','.join(child)
        if '&' in child:
            child = re.sub('&', parent, child)
        else:
            child = parent + ' ' + child
        for inner in dict_to_css(value, child, braces):
            if child.startswith('@') and not parent:
                inner = f' {braces[0]} {inner.strip()} {braces[1]}'
            yield inner


def dict_to_css(selectors: dict, parent: str = '', braces=('{', '}')):
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


def get_reference(tag: Tag):
    return f'[style-id="{tag.style_id}"]'


class Style(Tag, name='style', content_tag=None, raw_html=True, force_ref=True):
    __slots__ = ('styles', 'real_parent')
    __extra_attrs__ = ('style_id',)

    _global = {
        'styles_count': 1,
    }

    options = state(type=dict)
    real_parent: Optional[Tag]

    @classmethod
    def from_css(cls, file):
        # TODO: implement import from css/scss/pycss
        raise AttributeError

    def __init__(self, styles=None, options=None, get_vars=None, **styles_dict):
        super().__init__()
        if styles and not styles_dict:
            styles_dict = styles
        if options is None:
            options = {}
        self.styles = styles_dict
        self._content = ''
        self.real_parent = None
        self.options = {
            'global': False,
            'render_states': True,
            'render_children': True,
            'get_vars_callback': get_vars,
        } | options

    def __mount__(self, element, parent, index=None):
        self.real_parent = parent
        if __CONFIG__['style_head']:
            super().__mount__(Head.mount_element, Head)
        else:
            super().__mount__(element, parent, index)

    def __unmount__(self, element, parent, _unsafe=False):
        return super().__unmount__(element, parent, _unsafe=True)

    def mount(self):
        parent = self.real_parent

        if self.options['global']:  # TODO: add example
            self._content = '\n'.join(list(dict_to_css(self.styles, parent._tag_name_)))
            return

        if hasattr(parent, 'style_id'):  # support multiple style children
            style_id = parent.style_id
        else:
            self._global['styles_count'] += 1
            style_id = get_random_name(log10_ceil(self._global['styles_count']) + 1)
            attr(style_id, type=str)._link_ctx('style_id', parent)

        # TODO: is [style-id=] slow? If so, maybe use classes?
        self._content = '\n'.join(
            list(dict_to_css(self.styles, f'{parent._tag_name_}[style-id="{style_id}"]', braces=('{{', '}}')))
        )

    @safe_html.content
    def content(self):
        if self.options['global'] or not self._content:
            return self._content

        parent = self.real_parent

        params: dict[str, Any] = {}
        if self.options['render_states']:
            params.update(parent.__states__)
        if self.options['render_children']:
            params.update(parent.ref_children)
        if get_vars := self.options['get_vars_callback']:
            params.update(get_vars(self=parent, ref=get_reference, **params))

        # TODO: use native css '--var: {}' instead of re-render the whole content
        return self._content.strip().format(**params)

    @classmethod
    def import_file(cls, file_path):
        return js.beepy.addElement(
            js.document.head,
            'link',
            href=js.beepy.getPathWithCurrentPathAndOrigin(file_path),
            onload=cls.create_onload(),
            type='text/css',
            rel='stylesheet',
        )


def with_style(style_or_tag_cls: Optional[Style | Type[Tag]] = None):
    """
    @with_style
    class Button(Tag, name='button'):
        ...

    styled_button = with_style(Style(display='block', **kwargs))(button)
    """

    def wrapper(tag_cls: Type[Tag]):
        return type(tag_cls.__name__, (tag_cls,), {'style': style_or_tag_cls or Style()})

    if safe_issubclass(style_or_tag_cls, Tag):
        _tag_cls, style_or_tag_cls = style_or_tag_cls, None
        return wrapper(_tag_cls)

    return wrapper


__all__ = ['dict_to_css', 'Style', 'with_style']
