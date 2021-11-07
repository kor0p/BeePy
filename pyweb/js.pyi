from typing import Any, Union, Callable

document: Any

class Node:
    def appendChild(self, child: 'Node') -> 'Node':
        ...

    def append(self, *nodesOrDOMStrings: Union['Node', str]):
        ...

class HTMLElement(Node):
    _py: 'Tag'

    def setAttribute(self, name: str, value: Any):
        ...

    def addEventListener(self, type: str, listener: Callable):
        ...
