import re


def camel_or_snake_to_kebab_case(string: str):
    """
    parsing name of tag to html-compatible or name of property to css-compatible
    >>> class __pyx__(): ...  # <pyx></pyx>
    >>> class myTagName(): ...  # <my-tag-name/>
    >>> Style(font_size='20px')  # font-size: 20px
    >>> Style(backgroundColor='red')  # background-color: red
    """
    string = re.sub('_', '-', string)
    string = re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), string)
    return string
