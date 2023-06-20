#!/usr/bin/env python3
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


class Manager:
    def __init__(self):
        self.websockets = []
        self.root_path = ''
        self.observer = None

    def set_ws(self, websocket):
        self.websockets.append(websocket)

    async def ws_send(self, message):
        for ws in self.websockets[:]:
            try:
                await ws.send(message)
            except ConnectionClosedOK:
                self.websockets.remove(ws)

        if not self.websockets:
            print('No clients connected! Please, restart your page to connect to the dev server')

    def set_root_path(self, path):
        self.root_path = path

    def set_observer(self, observer):
        self.observer = observer


m = Manager()


# File Watcher


class MonitorFolder(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory or event.src_path.endswith(('~', '.tmp')) or event.event_type in ('opened', 'closed'):
            return

        path = event.src_path
        if path.startswith(m.root_path):
            path = path[len(m.root_path):]
        if path.startswith('.idea'):
            return

        asyncio.run(m.ws_send(path))


def start_watcher():
    root_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    event_handler = MonitorFolder()
    observer = Observer()
    observer.schedule(event_handler, path=root_path, recursive=True)
    print(f'Monitoring started for {root_path}')
    observer.start()
    m.set_root_path(root_path)
    m.set_observer(observer)
    try:
        while (True):
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        observer.join()


# WebSocket Server


async def echo(websocket):
    m.set_ws(websocket)

    async for message in websocket:
        print(f'{websocket=} {message=}')  # We really don't receive messages


async def main_ws():
    print('WebSockets started')
    async with serve(echo, 'localhost', 8998):
        await asyncio.Future()  # run forever


def start_websockets():
    asyncio.run(main_ws())


HTTP_PORT = 8888
Handler = http.server.SimpleHTTPRequestHandler


def start_http():
    with socketserver.TCPServer(('', HTTP_PORT), Handler) as httpd:
        print(f'Serving at port {HTTP_PORT}\nOpen server: http://localhost:{HTTP_PORT}')
        httpd.serve_forever()


Thread(target=start_watcher, daemon=True).start()
Thread(target=start_websockets, daemon=True).start()
Thread(target=start_http, daemon=True).start()
while True:
    time.sleep(60)
