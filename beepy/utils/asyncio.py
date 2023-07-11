import asyncio
import inspect
from functools import wraps

import beepy
from beepy.utils.js_py import js
from beepy.utils.dev import _debugger


def ensure_sync(to_await, callback=lambda x: x):
    if inspect.iscoroutine(to_await):
        task = asyncio.get_event_loop().run_until_complete(to_await)
        task.add_done_callback(callback)
        return task

    callback(to_await)
    return to_await


def force_sync(function):
    # TODO: maybe do it with class will be better?

    callbacks = []

    @wraps(function)
    def wrapper(*args, _done_callback_=None, **kwargs):
        current_callbacks = [(cb() if dynamic else cb) for cb, dynamic in callbacks]
        current_callbacks.append(_done_callback_)

        def _callback(_res_):
            try:
                r = _res_.result()
            except Exception as e:
                _debugger(e)
                return

            for cb in current_callbacks:
                if cb is None:
                    continue
                try:
                    cb(*args, **kwargs, _res_=r)
                except Exception as e:
                    _debugger(e)
        return ensure_sync(function(*args, **kwargs), _callback)

    wrapper.run_after = wrapper.add_callback = lambda fn: callbacks.append((fn, False)) or fn
    wrapper.add_dynamic_callback = lambda fn: callbacks.append((fn, True)) or fn

    return wrapper


def force_sync__wait_load(function):
    wrapper = force_sync(function)
    wrapper.add_dynamic_callback(beepy.context.Context.create_onload)
    return wrapper


force_sync.wait_load = force_sync__wait_load


delay = js.delay


@force_sync
async def sleep(s):  # TODO: check if this actually works or not
    return await js.delay(s * 1000)


__all__ = ['ensure_sync', 'force_sync', 'delay', 'sleep']
