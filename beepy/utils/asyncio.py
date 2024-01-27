import asyncio
import inspect
from functools import wraps

import beepy


async def ensure_async(coro_or_result):
    if inspect.iscoroutine(coro_or_result):
        return await coro_or_result
    else:
        return coro_or_result


def ensure_sync(coro_or_result):
    if inspect.iscoroutine(coro_or_result):
        return syncify(coro_or_result)
    else:
        return coro_or_result


def syncify(coro):
    return asyncio.create_task(coro).syncify()


def syncify_func(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        return syncify(function(*args, **kwargs))

    return wrapper


async def _gather(*coros):
    return await asyncio.gather(*coros)


def syncify_many(*coros):
    return asyncio.create_task(_gather(*coros)).syncify()


def execute_before_load(coro):
    waiter = beepy.context.Context.create_onload()
    try:
        return syncify(coro)
    finally:
        waiter()


def before_load(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        return execute_before_load(function(*args, **kwargs))

    return wrapper


sleep = syncify_func(asyncio.sleep)


__all__ = ['syncify', 'syncify_func', 'syncify_many', 'execute_before_load', 'before_load', 'sleep']
