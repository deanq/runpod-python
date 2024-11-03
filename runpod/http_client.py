"""
HTTP Client abstractions with OpenTelemetry tracing support.
"""

import os
import requests
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientResponseError
from opentelemetry import trace
from opentelemetry.instrumentation.aiohttp_client import create_trace_config
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from .cli.groups.config.functions import get_credentials
from .user_agent import USER_AGENT

tracer = trace.get_tracer(__name__)


class TooManyRequests(ClientResponseError):
    pass


def get_auth_header():
    """
    Produce a header dict with the `Authorization` key derived from
    credentials.get("api_key") OR os.getenv('RUNPOD_AI_API_KEY')
    """
    if credentials := get_credentials():
        auth = credentials.get("api_key", "")
    else:
        auth = os.getenv("RUNPOD_AI_API_KEY", "")

    return {
        "Content-Type": "application/json",
        "Authorization": auth,
        "User-Agent": USER_AGENT,
    }


def AsyncClientSession(*args, **kwargs):
    """
    Factory method for an async client session with OpenTelemetry tracing.
    """
    return ClientSession(
        connector=TCPConnector(limit=0),
        headers=get_auth_header(),
        timeout=ClientTimeout(600, ceil_threshold=400),
        trace_configs=[create_trace_config()],
        *args,
        **kwargs,
    )


class SyncClientSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.headers.update(get_auth_header())
        RequestsInstrumentor().instrument_session(self)
