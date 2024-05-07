import pathlib

import click

from beepy.dev import DevServer
from beepy.ssr import create_ssr_dist

DirType = click.Path(exists=True, file_okay=False, path_type=pathlib.Path)


@click.group('BeePy commands')
def main():
    pass


@main.command('Simple dev server for BeePy')
@click.option(
    '-d', '--root-dir', default=None, type=DirType, help='Root directory to start server and watch file changes'
)
@click.option('-p', '--port', default=8888, type=click.INT, show_default=True, help='Port for the server')
@click.option('--create', type=click.BOOL, help='Create a default .html, .py and .env files before start')
@click.option('--ssr', type=click.BOOL, help='Save rendered HTML on server-side (in /dist). Requires [ssr] dependency')
def server(root_dir, port, create, ssr):
    DevServer(root=root_dir, port=port, create=create, ssr=ssr).start(start_http=True)


@main.command('Build SSR pages. Requires [ssr] dependency')
@click.option('-d', '--root-dir', default=None, type=DirType, help='Root, where will be created /dist directory')
@click.option(
    '--server', default='http://localhost:8888', show_default=True, help='Base URL of the running BeePy server'
)
@click.option('--index', default='/', show_default=True, help='URL of the index page')
def build(root_dir, server, index):
    create_ssr_dist(root_dir, server, index)


if __name__ == '__main__':
    main()
