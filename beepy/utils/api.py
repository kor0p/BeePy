import dataclasses
import json
from datetime import datetime
from http.client import HTTPException

from pyodide import http as pyodide_http

from beepy.utils.js_py import IN_BROWSER
from beepy.utils.internal import __CONFIG__


class UpgradedJSONEncoder(json.JSONEncoder):  # TODO: consider on rewriting json.JSONEncoder
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime):
            return o.strftime(__CONFIG__['default_datetime_format'])
        return super().default(o)


async def request(url, method='GET', body=None, headers=None, **opts):
    if body is not None:
        body = json.dumps(body, cls=UpgradedJSONEncoder)

    if headers is None:
        headers = {}

    headers.update(
        {
            'mode': 'no-cors',
            'Content-Type': 'application/json',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
        }
    )

    response = await pyodide_http.pyfetch(
        __CONFIG__['api_url'] + url, method=method, body=body, headers=headers, **opts
    )

    if int(response.status) >= 400:
        raise HTTPException(response.status)

    if method == 'GET' or opts.get('to_json'):
        response = await response.json()
    else:
        response = await response.string()

    return response


if not IN_BROWSER:
    import requests

    async def request(url, method='GET', body=None, headers=None, **opts):
        if body is not None:
            body = json.dumps(body, cls=UpgradedJSONEncoder)

        if headers is None:
            headers = {}

        # TODO: check opts argument compatibility

        response = requests.request(method, __CONFIG__['api_url'] + url, data=body, headers=headers)

        if int(response.status_code) >= 400:
            raise HTTPException(response.status_code)

        if method == 'GET' or opts.get('to_json'):
            response = response.json()
        else:
            response = response.text

        return response


__all__ = ['request', 'UpgradedJSONEncoder']
