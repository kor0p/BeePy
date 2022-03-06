import re
import math
from typing import Any

# [PYWEB IGNORE START]
from .framework import Tag, attr, state
from .utils import get_random_name, to_kebab_case
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


class style(Tag, name='style', content_tag=None):
    _global = {
        'styles_count': 0
    }

    options: dict = state()

    def __init__(self, options=None, **styles):
        if options is None:
            options = {}
        self.styles = styles
        self._content = ''
        super().__init__(options=options | {'global': False, 'render_states': True, 'render_children': True})
        if not self.options['global']:
            self._global['styles_count'] += 1

    def mount(self):
        parent = self.parent

        if self.options['global']:
            self._content = '\n'.join(list(dict_to_css(self.styles, parent._tag_name_)))
            return

        name = get_random_name(math.ceil(math.log10(self._global['styles_count'])))
        attribute = attr(name)
        attribute.__set_to_tag__('style_id', parent, force=True)
        attribute.__set_type__(str)

        self._content = '\n'.join(
            list(dict_to_css(self.styles, f'{parent._tag_name_}[style-id="{name}"]', braces=('{{', '}}')))
        )

    def content(self):
        if self.options['global']:
            return self._content

        params: dict[str, Any] = dict(self=self.parent)
        if self.options['render_states']:
            params.update(self.parent.__states__)
        if self.options['render_children']:
            params['children'] = self.parent.children
            params.update(self.parent.ref_children)
        return self._content.format(**params)
