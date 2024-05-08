import pathlib

import click

from beepy.dev import DevServer
from beepy.ssr import create_ssr_dist

DirType = click.Path(exists=True, file_okay=False, path_type=pathlib.Path)


@click.group()
def main():
    """BeePy commands"""


@main.command()
@click.option(
    '-d', '--root-dir', default=None, type=DirType, help='Root directory to start server and watch file changes'
)
@click.option('-p', '--port', default=8888, type=click.INT, show_default=True, help='Port for the server')
@click.option('--init', is_flag=True, help='Create a default .html, .py and .env files before start')
@click.option('--ssr', is_flag=True, help='Save rendered HTML on server-side (in /dist). Requires [ssr] dependency')
def dev(root_dir, port, init, ssr):
    """Simple dev server for BeePy"""
    DevServer(root=root_dir, port=port, init=init, ssr=ssr).start(start_http=True)


@main.command()
@click.option('-d', '--root-dir', default=None, type=DirType, help='Root, where will be created /dist directory')
@click.option(
    '--server', default='http://localhost:8888', show_default=True, help='Base URL of the running BeePy server'
)
@click.option('--index', default='/', show_default=True, help='URL of the index page')
def build(root_dir, server, index):
    """Build SSR pages. Requires [ssr] dependency"""
    create_ssr_dist(root_dir or pathlib.Path.cwd(), server, index)


if __name__ == '__main__':
    main()
