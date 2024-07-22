import aiohttp
import requests
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor, 
    ConsoleSpanExporter,
)
from opentelemetry import trace


# Set up OpenTelemetry
resource = Resource(attributes={"service.name": "aiohttp-client"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)


# Enable instrumentation
AioHttpClientInstrumentor().instrument()
RequestsInstrumentor().instrument()


class AsyncClientSession(aiohttp.ClientSession):
    def __init__(self, *args, **kwargs):
        trace_config = AioHttpClientInstrumentor().create_trace_config()
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
