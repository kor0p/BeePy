#!/usr/bin/env python3
import os

try:
    import websockets as _
except ImportError:
    print('Did you forget to install dev-requirements.txt?')
    exit(1)

import sys
import time
import asyncio
from threading import Thread
from websockets.server import serve
from websockets.exceptions import ConnectionClosedOK
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Manager:
    def __init__(self):
        self.websockets = []
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

    def set_observer(self, observer):
        self.observer = observer


m = Manager()


class MonitorFolder(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory or event.src_path.endswith('~') or event.event_type in ('opened', 'closed'):
            return

        asyncio.run(m.ws_send(f'{event.src_path=} {event.event_type=}'))
        print(event.src_path, event.event_type)


def start_watcher():
    src_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    event_handler = MonitorFolder()
    observer = Observer()
    observer.schedule(event_handler, path=src_path, recursive=True)
    print(f'Monitoring started for {src_path}')
    observer.start()
    m.set_observer(observer)
    try:
        while (True):
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        observer.join()


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


Thread(target=start_watcher, daemon=True).start()
Thread(target=start_websockets, daemon=True).start()
while True:
    time.sleep(60)
