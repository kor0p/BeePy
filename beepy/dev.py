#!/usr/bin/env python3
import functools
import os

import sys
import time
import asyncio
import http.server
import socketserver
from threading import Thread
from websockets.server import serve
from websockets.exceptions import ConnectionClosedOK
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class MonitorFolder(FileSystemEventHandler):
    def __init__(self, server):
        self.server = server

    def on_any_event(self, event):
        self.server.handle_file_event(event)


class DevServer:
    def __init__(self):
        self.websockets = []
        self.root_path = None
        self.observer = None

    async def ws_send(self, message):
        await asyncio.sleep(1)  # Hack for Django autoreload

        for ws in self.websockets[:]:
            try:
                await ws.send(message)
            except ConnectionClosedOK:
                self.websockets.remove(ws)

        if not self.websockets:
            print('[BeePy] No clients connected! Please, restart your page to connect to the dev server')

    def handle_file_event(self, event):
        path = event.src_path
        if (
            event.is_directory
            or event.src_path.endswith(('~', '.tmp'))
            or '/__pycache__/' in path
            or '/.idea/' in path
            or event.event_type in ('opened', 'closed')
        ):
            return

        if path.startswith(self.root_path):
            path = path[len(self.root_path): ]
        if path.startswith('/'):
            path = path[1:]

        print(f'[BeePy] Found file change: {path}')
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
        with socketserver.TCPServer(
            ('', port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=self.root_path)
        ) as httpd:
            print(f'[BeePy] Serving at port {port}\nOpen server: http://localhost:{port}')
            httpd.serve_forever()

    def start(self, start_http=None, root_path=None, wait=False):
        if self.observer is not None:
            print('[BeePy] Server is already started')
            return

        if root_path is None:
            root_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

        self.root_path = root_path

        Thread(target=self._ws_start, daemon=True).start()
        Thread(target=self._watcher_start, daemon=True).start()
        if start_http is not None:
            Thread(target=start_http, daemon=True).start()
        if wait:
            while True:
                time.sleep(3600)


dev_server = DevServer()
start_simple_dev_server = functools.partial(dev_server.start, start_http=dev_server._simple_http_start, wait=True)


if __name__ == '__main__':
    start_simple_dev_server()
