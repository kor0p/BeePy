import re

# [PYWEB IGNORE START]
from .framework import Tag
from .utils import camel_or_snake_to_kebab_case
# [PYWEB IGNORE END]

SPACES_4 = '    '


def dict_of_properties_to_css(properties):
    for prop, value in properties.items():
        if not isinstance(prop, (tuple, set)):
            prop = (prop,)
        result = ''
        for _property in prop:
            _property = camel_or_snake_to_kebab_case(_property)

            # if '&' in _property:
            #     _property = re.sub('&', parent, _property)
            result += SPACES_4 + _property
            if isinstance(value, (list, tuple)):  # handle raw css
                result += ' ' + (_property + ' ').join(x for x in value if x)
            else:
                result += f': {value};'
        yield result


def dict_of_parents_to_css(children, parent):
    for child, value in children.items():
        if isinstance(child, (tuple, set)):
            child = ','.join(child)
        if '&' in child:
            child = re.sub('&', parent, child)
        else:
            child = parent + ' ' + child
        for inner in dict_to_css(value, child):
            if child.startswith('@') and not parent:
                inner = f' {{ {inner.strip()} }}'
            yield inner


def dict_to_css(selectors: dict, parent: str = ''):
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
                )
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
        yield parent + ' {'
        yield from dict_of_properties_to_css(properties)
        yield '}'

    yield from dict_of_parents_to_css(children, parent)


class style(Tag, name='style', raw_content=True):
    def __init__(self, **styles):
        self.styles = styles
        super().__init__()

    def content(self):
        return '\n'.join(
            list(dict_to_css(self.styles, self.parent._name))
        )
