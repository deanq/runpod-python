import aiohttp
import os
import requests
from .tracer import (
    get_aiohttp_tracer,
    get_request_tracer,
)
from .user_agent import USER_AGENT
from .cli.groups.config.functions import get_credentials


def get_auth_header():
    if credentials := get_credentials():
        auth = credentials.get("api_key")
    else:
        auth = os.environ.get('RUNPOD_AI_API_KEY')

    return {
        "Content-Type": "application/json",
        "Authorization": f"{auth}",
        "User-Agent": USER_AGENT,
    }


class AsyncClientSession(aiohttp.ClientSession):
    def __init__(self, *args, **kwargs):
        super().__init__(
            connector=aiohttp.TCPConnector(limit=0),
            headers=get_auth_header(),
            timeout=aiohttp.ClientTimeout(600, ceil_threshold=400),
            trace_configs=[get_aiohttp_tracer()],
            *args,
            **kwargs,
        )


class SyncClientSession(requests.Session):
    def request(self, method, url, **kwargs):
        with get_request_tracer() as tracer:
            # Separate out the kwargs that are not applicable to `requests.Request`
            request_kwargs = {
                k: v for k, v in kwargs.items() if k in requests.Request.__init__.__code__.co_varnames
            }
            send_kwargs = {
                k: v for k, v in kwargs.items() if k not in request_kwargs
            }
            
            # Create a PreparedRequest object to hold the request details
            req = requests.Request(method, url, **request_kwargs)
            prepped = self.prepare_request(req)
            tracer.request = prepped  # Assign the request to the tracer
            
            # Merge environment settings
            settings = self.merge_environment_settings(
                prepped.url,
                send_kwargs.get('proxies'),
                send_kwargs.get('stream'),
                send_kwargs.get('verify'), 
                send_kwargs.get('cert'),
            )
            send_kwargs.update(settings)
            
            # Send the request
            response = self.send(prepped, **send_kwargs)
            tracer.response = response  # Assign the response to the tracer
            
            return response
