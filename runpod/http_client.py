import aiohttp
import requests
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor, create_trace_config
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from .observability import trace


# Enable instrumentation
AioHttpClientInstrumentor().instrument()
RequestsInstrumentor().instrument()


class AsyncClientSession(aiohttp.ClientSession):
    def __init__(self, *args, **kwargs):
        trace_config = create_trace_config()
        super().__init__(trace_configs=[trace_config], *args, **kwargs)
        self.tracer = trace.get_tracer(__name__)

    def get_tracer(self):
        return self.tracer



class SyncClientSession(requests.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracer = trace.get_tracer(__name__)

    def get_tracer(self):
        return self.tracer
