import inspect
import traceback

from beepy.utils.js_py import js, log, to_js


def _debugger(error=None):
    if isinstance(error, Exception):
        log.warn(traceback.format_exc())
        error_frame = tuple(traceback.walk_tb(error.__traceback__))[-1][0]
    else:
        log.warn(''.join(traceback.format_stack()[:-1]))
        log.warn(error)
        error_frame = None

    frame = inspect.currentframe().f_back
    js._locals = to_js(frame.f_locals)
    js._locals._frame = frame
    js._locals.error_frame = error_frame
    js._DEBUGGER(error)


__all__ = ['_debugger']
