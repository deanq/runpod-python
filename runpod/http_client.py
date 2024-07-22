import aiohttp
from opentelemetry.instrumentation.aiohttp_client import (
    AioHttpClientInstrumentor
)
import requests
from opentelemetry.instrumentation.requests import (
    RequestsInstrumentor
)


# Enable instrumentation
AioHttpClientInstrumentor().instrument()
RequestsInstrumentor().instrument()


class AsyncClientSession(aiohttp.ClientSession):
    pass


class SyncClientSession(requests.Session):
    pass
