import os
import typing
import aiohttp
from requests import PreparedRequest, Response

from opentelemetry import trace
from opentelemetry.sdk.trace import Resource, TracerProvider, Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

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
                "service.name": "runpod-python-sdk",
                "service.version": runpod_version,
                "application": "runpod-serverless",
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
def requests_request_hook(span: Span, request_obj: PreparedRequest):
    pass


def requests_response_hook(
    span: Span, request_obj: PreparedRequest, response: Response
):
    pass


RequestsInstrumentor().instrument()


# --- aiohttp --- #
def aiohttp_request_hook(span: Span, params: aiohttp.TraceRequestStartParams):
    if span and span.is_recording():
        span.set_attribute(
            "custom_user_attribute_from_request_hook", "aiohttp_request_hook"
        )


def aiohttp_response_hook(
    span: Span,
    params: typing.Union[
        aiohttp.TraceRequestEndParams,
        aiohttp.TraceRequestExceptionParams,
    ],
):
    if span and span.is_recording():
        span.set_attribute(
            "custom_user_attribute_from_response_hook", "aiohttp_response_hook"
        )


AioHttpClientInstrumentor().instrument()
