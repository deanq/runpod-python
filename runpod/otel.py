import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import (
    Resource,
    SERVICE_NAME,
    SERVICE_VERSION,
    HOST_NAME,

)

from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.threading import ThreadingInstrumentor
from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor

from runpod.version import __version__ as runpod_version


trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create(
            {
                "application": "runpod-serverless",
                SERVICE_NAME: "runpod-python-sdk",
                SERVICE_VERSION: runpod_version,
                HOST_NAME: os.getenv("RUNPOD_POD_HOSTNAME"),
            }
        )
    )
)

tracer = trace.get_tracer_provider()

if os.getenv("RUNPOD_LOG_LEVEL", "").lower() == "trace":
    tracer.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))


# --- threading --- #
ThreadingInstrumentor().instrument()


# --- urllib3 --- #
URLLib3Instrumentor().instrument()


# --- asyncio --- #
AsyncioInstrumentor().instrument()


# --- requests --- #
RequestsInstrumentor().instrument()


# --- aiohttp --- #
AioHttpClientInstrumentor().instrument()
