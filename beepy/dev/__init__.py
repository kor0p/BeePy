#!/usr/bin/env python3
import asyncio
import functools
import http.server
import os
import re
import shutil
import socketserver
import subprocess
import time
from pathlib import Path
from threading import Thread

import dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from websockets.exceptions import ConnectionClosedOK
from websockets.server import serve

from beepy.ssr import get_server_html

dotenv.load_dotenv()
BASE_DIR = Path(__file__).resolve().parent


class MonitorFolder(FileSystemEventHandler):
    def __init__(self, server):
        self.server = server

    def on_any_event(self, event):
        if not (
            event.event_type in ('opened', 'closed')
            or event.is_directory
            or event.src_path.endswith(('~', '.tmp'))
            or re.search(r'/(__pycache__|.git|.idea|dist|build)/', event.src_path)
        ):
            self.server._handle_file_event(event)


class DevServer:
    def __init__(self, *, root=None, port=8888, init=False, ssr=False):
        self.websockets = []
        self.root = (root or Path.cwd()).resolve()
        self.port = port
        self.ssr = ssr

        self.observer = None
        self.developer_mode = os.environ.get('DEVELOPMENT') == '1'

        if init:
            self._create_default_files()

    def _create_default_files(self):
        dst = self.root / 'index.html'

        if dst.exists():
            print('[BeePy] Warning: File "index.html" already exists, skipping creating default files')
            return

        shutil.copyfile(BASE_DIR / 'example.html', dst)
        shutil.copyfile(BASE_DIR / 'example.py', self.root / '__init__.py')
        shutil.copyfile(BASE_DIR / '.env.example', self.root / '.env')
        print('[BeePy] Created default files in root directory')

    def _ssr_create_dist(self):
        if not self.ssr:
            return

        dist = Path(self.root / 'dist')
        dist.mkdir(parents=True, exist_ok=True)

        # TODO: add support for Router (load_all_routes=True)
        ssr_data = get_server_html(f'http://localhost:{self.port}', '/')
        (dist / 'index.html').write_text(ssr_data)
        shutil.copyfile(self.root / '__init__.py', dist / '__init__.py')
        print(f'[BeePy] [SSR] dist is done. Visit: http://localhost:{self.port}')

    async def ws_send(self, message):
        await asyncio.sleep(1)  # Hack for Django autoreload

        for ws in self.websockets[:]:
            try:
                await ws.send(message)
            except ConnectionClosedOK:
                self.websockets.remove(ws)

        if not self.websockets:
            print('[BeePy] No clients connected! Please, restart your page to connect to the dev server')

    def _handle_file_event(self, event):
        path: str = event.src_path.removeprefix(str(self.root)).removeprefix('/')

        print(f'[BeePy] Found file change: {path}')
        if self.developer_mode:
            if path.endswith('.py'):
                subprocess.call('hatch build', shell=True)
            elif path.endswith('.js'):
                subprocess.call(f'cd {self.root}/web; npm run build; cd -', shell=True)  # rebuild dist
            path = '__'

        self._ssr_create_dist()
        asyncio.run(self.ws_send(path))

    def _watcher_start(self):
        event_handler = MonitorFolder(self)
        observer = Observer()
        observer.schedule(event_handler, path=str(self.root), recursive=True)
        print(f'[BeePy] Monitoring started for {self.root}')
        observer.start()
        self.observer = observer
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            observer.join()

    async def _ws_echo(self, websocket):
        self.websockets.append(websocket)

        async for message in websocket:
            print(f'{websocket=} {message=}')  # We really don't receive messages

    async def _ws_main(self):
        print('[BeePy] WebSockets started')
        async with serve(self._ws_echo, 'localhost', 8998):
            await asyncio.Future()  # run forever

    def _ws_start(self):
        asyncio.run(self._ws_main())

    def _simple_http_start(self):
        # Fixes "Address already in use"
        socketserver.TCPServer.allow_reuse_address = True

        with socketserver.TCPServer(
            ('', self.port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=self.root)
        ) as httpd:
            print(f'[BeePy] Serving at port {self.port}\nOpen server: http://localhost:{self.port}')
            httpd.serve_forever()

    def start(self, *, start_http=False, forever=True):
        if self.observer is not None:
            print('[BeePy] Server is already started')
            return

        Thread(target=self._ws_start, daemon=True).start()
        Thread(target=self._watcher_start, daemon=True).start()

        if not start_http:
            return

        if start_http is True:
            start_http = self._simple_http_start

        thread = Thread(target=start_http, daemon=True)
        thread.start()
        self._ssr_create_dist()
        if forever:
            thread.join()


__all__ = ['DevServer']
