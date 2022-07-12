import re
from typing import Any, Optional, Type

from .framework import __CONFIG__, Tag, attr, state
from .utils import log10_ceil, get_random_name, to_kebab_case, safe_eval
from .tags import Head


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

            # if '&' in _property:
            #     _property = re.sub('&', parent, _property)
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


class style(Tag, name='style', content_tag=None, raw_html=True, force_ref=True):
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

    def __init__(self, styles=None, options=None, **styles_dict):
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
        } | options

    def __mount__(self, element, parent, index=None):
        self.real_parent = parent
        if __CONFIG__['style_head']:
            super().__mount__(Head.mount_element, Head)
        else:
            super().__mount__(element, parent, index)

    def mount(self):
        parent = self.real_parent

        if self.options['global']:  # TODO: add example
            self._content = '\n'.join(list(dict_to_css(self.styles, parent._tag_name_)))
            return
        else:
            self._global['styles_count'] += 1

        if hasattr(parent, 'style_id'):  # support multiple style children
            style_id = parent.style_id
            self._global['styles_count'] -= 1
        else:
            style_id = get_random_name(log10_ceil(self._global['styles_count']))
            attr(style_id, type=str)._link_ctx('style_id', parent)

        # TODO: is [style-id=] slow? If so, maybe use classes?
        self._content = '\n'.join(
            list(dict_to_css(self.styles, f'{parent._tag_name_}[style-id="{style_id}"]', braces=('{{', '}}')))
        )

    def content(self):
        if self.options['global'] or not self._content:
            return self._content

        parent = self.real_parent

        params: dict[str, Any] = dict(self=parent, ref=self.get_reference)
        if self.options['render_states']:
            params.update(parent.__states__)
        if self.options['render_children']:
            params['children'] = parent.children
            params.update(parent.ref_children)
        # TODO: use native css '--var: {}' instead of re-render the whole content
        return safe_eval(f'f"""{self._content.strip()}"""', params)

    def get_reference(self, tag: Tag):
        return f'[style-id="{tag.style_id}"]'


def with_style(_style: Optional[style] = None):
    def wrapper(tag_cls: Type[Tag]):
        return type(tag_cls.__name__, (tag_cls,), {"style": _style or style()})

    return wrapper


__all__ = ['dict_to_css', 'style', 'with_style']
