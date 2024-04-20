import dataclasses
import json
from datetime import datetime
from http import HTTPStatus
from http.client import HTTPException

from beepy.utils.internal import __config__
from beepy.utils.js_py import IN_BROWSER


class UpgradedJSONEncoder(json.JSONEncoder):  # TODO: consider on rewriting json.JSONEncoder
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime):
            return o.strftime(__config__['default_datetime_format'])
        return super().default(o)


if IN_BROWSER:
    from pyodide.http import pyfetch

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
            },
        )

        response = await pyfetch(__config__['api_url'] + url, method=method, body=body, headers=headers, **opts)

        try:
            response.raise_for_status()
        except OSError as err:
            raise HTTPException(err) from err

        return (await response.json()) if method in ('GET', 'PUT', 'POST') else (await response.text())

else:
    import requests

    async def request(url, method='GET', body=None, headers=None, **_opts):
        if body is not None:
            body = json.dumps(body, cls=UpgradedJSONEncoder)

        if headers is None:
            headers = {}

        # TODO: check opts argument compatibility

        response = requests.request(method, __config__['api_url'] + url, data=body, headers=headers)

        if int(response.status_code) >= HTTPStatus.BAD_REQUEST:
            raise HTTPException(response.status_code)

        return response.json() if method in ('GET', 'PUT', 'POST') else response.text


__all__ = ['request', 'UpgradedJSONEncoder']
