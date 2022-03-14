import re
import math
from typing import Any, Optional

# [PYWEB IGNORE START]
from .framework import __CONFIG__, Tag, attr, state
from .utils import get_random_name, to_kebab_case, safe_eval
from .tags import Head
# [PYWEB IGNORE END]

SPACES_4 = '    '


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
            result += SPACES_4 + _property
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


class style(Tag, name='style', content_tag=None, raw_html=True):
    _global = {
        'styles_count': 1,
    }

    options: dict = state()
    real_parent: Optional[Tag]

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

    def __mount__(self, element, index=None):
        self.real_parent = element._py
        if not __CONFIG__['debug']:
            super().__mount__(element, index)
            return

        super().__mount__(Head.mount_element)

    def mount(self):
        parent = self.real_parent

        if self.options['global']:
            self._content = '\n'.join(list(dict_to_css(self.styles, parent._tag_name_)))
            return
        else:
            self._global['styles_count'] += 1

        if hasattr(parent, 'style_id'):  # support multiple style children
            name = parent.style_id
            self._global['styles_count'] -= 1
        else:
            name = get_random_name(math.ceil(math.log10(self._global['styles_count'])))
            attribute = attr(name)
            attribute.__set_to_tag__('style_id', parent, force=True)
            attribute.__set_type__(str)

        self._content = '\n'.join(
            list(dict_to_css(self.styles, f'{parent._tag_name_}[style-id="{name}"]', braces=('{{', '}}')))
        )

    def content(self):
        if self.options['global'] or not self._content:
            return self._content

        parent = self.real_parent

        params: dict[str, Any] = dict(self=parent)
        if self.options['render_states']:
            params.update(parent.__states__)
        if self.options['render_children']:
            params['children'] = parent.children
            params.update(parent.ref_children)
        # TODO: use native css '--var: {}' instead of re-render the whole content
        return safe_eval(f'f"""{self._content.strip()}"""', params)
