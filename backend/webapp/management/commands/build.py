import os  # noqa: INP001
import subprocess
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from beepy.ssr import create_ssr_dist


class Command(BaseCommand):
    help = 'Build a SSR static pages'

    def add_arguments(self, parser):
        parser.add_argument('--port', type=int)

    def handle(self, *args, port, **kwargs):  # noqa: ARG002 - unused args and kwargs
        manage_py_script = (settings.BASE_DIR / 'manage.py').resolve()
        subprocess.Popen(
            f'{manage_py_script} runserver {port}'.split(' '),
            env=os.environ | {'USE_SERVER_SIDE': '0', 'DEVELOPMENT': '0'},
        )
        time.sleep(2)

        create_ssr_dist(settings.STATICFILES_DIRS[0], f'http://0.0.0.0:{port}', '/e/')

        os.system(f'pkill -9 -f "runserver {port}"')  # I don't understand why other ways to stop Popen doesn't work :(
        time.sleep(1)
