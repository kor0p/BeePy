from __future__ import annotations

from beepy.tags import button


class Action(button, _root=True):
    components: dict[str, type[Action]] = {}

    action_name: str

    @classmethod
    def __class_declared__(cls):
        cls.components[cls.action_name] = cls
