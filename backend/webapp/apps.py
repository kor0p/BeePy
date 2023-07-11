import os
import sys
from pathlib import Path

from django.apps import AppConfig


class WebappConfig(AppConfig):
    name = 'webapp'

    def ready(self):
        if 'runserver' not in sys.argv or os.environ.get('RUN_MAIN'):  # reload
            return True

        from django.conf import settings

        if settings.DEBUG:
            from beepy.dev import dev_server
            dev_server.start(root_path=str(Path(__file__).parent.parent))
