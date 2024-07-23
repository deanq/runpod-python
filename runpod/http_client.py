import aiohttp
import os
import requests
from .tracer import get_aiohttp_tracer
from .user_agent import USER_AGENT


def get_auth_header():
    return {
        "Content-Type": "application/json",
        "Authorization": f"{os.environ.get('RUNPOD_AI_API_KEY')}",
        "User-Agent": USER_AGENT,
    }


class AsyncClientSession(aiohttp.ClientSession):
    def __init__(self, *args, **kwargs):
        super().__init__(
            connector=aiohttp.TCPConnector(limit=None),
            headers=get_auth_header(),
            timeout=aiohttp.ClientTimeout(600, ceil_threshold=400),
            trace_configs=[get_aiohttp_tracer()],
            *args,
            **kwargs,
        )


class SyncClientSession(requests.Session):
    def request(self, method, url, **kwargs):
        response = super().request(method, url, **kwargs)
        return response
