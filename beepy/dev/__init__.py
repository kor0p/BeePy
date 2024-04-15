#!/usr/bin/env python3
import argparse
import asyncio
import functools
import http.server
import os
import re
import shutil
import socketserver
import time
from pathlib import Path
from threading import Thread

import dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from websockets.exceptions import ConnectionClosedOK
from websockets.server import serve

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
    def __init__(self, *, root_path=None, parse_cmd=True):
        self.websockets = []
        self.root_path = root_path
        self.observer = None
        self.developer_mode = 'DEVELOPMENT' in os.environ
        if parse_cmd:
            self._handle_cmd_args()

    def _handle_cmd_args(self):
        parser = argparse.ArgumentParser(prog='beepy.dev', description='Simple dev server for BeePy')
        parser.add_argument(
            '-d', '--root-dir', default=Path.cwd(), help='Root directory to start server and watch file changes'
        )
        parser.add_argument(
            '--create', action='store_true', help='Create a default .html, .py and .env files before start'
        )
        args = parser.parse_args()

        if not self.root_path:
            self.root_path = Path(args.root_dir)

        if not args.create:
            return

        dst = self.root_path / 'index.html'

        if dst.exists():
            print('[BeePy] Warning: File "index.html" already exists, skipping creating default files')
            return

        shutil.copyfile(BASE_DIR / 'example.html', dst)
        shutil.copyfile(BASE_DIR / 'example.py', self.root_path / '__init__.py')
        shutil.copyfile(BASE_DIR / '../.env', self.root_path / '.env')
        print('[BeePy] Created default files in root directory')

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
        path: str = event.src_path.removeprefix(str(self.root_path)).removeprefix('/')

        print(f'[BeePy] Found file change: {path}')
        if self.developer_mode:
            if path.endswith('.py'):
                os.system('hatch build')
            elif path.endswith('.js'):
                os.system(f'cd {self.root_path}/web; npm run build; cd -')  # rebuild dist
            asyncio.run(self.ws_send('__'))
        else:
            asyncio.run(self.ws_send(path))

    def _watcher_start(self):
        event_handler = MonitorFolder(self)
        observer = Observer()
        observer.schedule(event_handler, path=self.root_path, recursive=True)
        print(f'[BeePy] Monitoring started for {self.root_path}')
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

    def _simple_http_start(self, port=8888):
        # Fixes "Address already in use"
        socketserver.TCPServer.allow_reuse_address = True

        with socketserver.TCPServer(
            ('', port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=self.root_path)
        ) as httpd:
            print(f'[BeePy] Serving at port {port}\nOpen server: http://localhost:{port}')
            httpd.serve_forever()

    def start(self, *, start_http=True, forever=True):
        if self.observer is not None:
            print('[BeePy] Server is already started')
            return

        Thread(target=self._ws_start, daemon=True).start()
        Thread(target=self._watcher_start, daemon=True).start()

        if not start_http:
            return

        if start_http is True:
            start_http = self._simple_http_start

        if forever:
            start_http()
        else:
            Thread(target=start_http, daemon=True).start()


__all__ = ['DevServer']
