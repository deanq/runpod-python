import aiohttp
from opentelemetry.instrumentation.aiohttp_client import (
    AioHttpClientInstrumentor
)


# Enable instrumentation
AioHttpClientInstrumentor().instrument()


class AsyncClientSession(aiohttp.ClientSession):
    pass
