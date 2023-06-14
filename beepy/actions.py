from __future__ import annotations

from typing import Type

from beepy.tags import button


class Action(button, _root=True):
    components: dict[str, Type[Action]] = {}

    action_name: str

    @classmethod
    def __class_declared__(cls):
        super().__class_declared__()

        cls.components[cls.action_name] = cls
