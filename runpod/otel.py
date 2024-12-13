import os
import logging
from typing import List

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import SpanExporter, BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import (
    Resource,
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME,
    SERVICE_VERSION,
)
from runpod.version import __version__ as runpod_version


log = logging.getLogger(__name__)
FMT = "%(filename)-20s:%(lineno)-4d %(asctime)s %(message)s"
logging.basicConfig(level=logging.INFO, format=FMT, handlers=[logging.StreamHandler()])


OTEL_COLLECTOR = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_SAMPLING_RATE = float(os.getenv("OTEL_SAMPLING_RATE", "0.01"))
RUNPOD_ENDPOINT_ID = "runpod.endpoint_id"
RUNPOD_ENDPOINT_ID_VALUE = os.getenv("RUNPOD_ENDPOINT_ID", "")
RUNPOD_POD_ID = "runpod.pod_id"
RUNPOD_POD_ID_VALUE = os.getenv("RUNPOD_POD_ID", "")
RUNPOD_ENV = os.getenv("ENV", "local")


if os.getenv("RUNPOD_LOG_LEVEL", "").lower() == "trace":
    log.setLevel(logging.TRACE)
    sampler = sampling.ALWAYS_ON
else:
    sampler = sampling.TraceIdRatioBased(OTEL_SAMPLING_RATE)

otlp_provider = TracerProvider(
    sampler=sampler,
    resource=Resource.create(
        {
            DEPLOYMENT_ENVIRONMENT: RUNPOD_ENV,
            RUNPOD_ENDPOINT_ID: RUNPOD_ENDPOINT_ID_VALUE,
            RUNPOD_POD_ID: RUNPOD_POD_ID_VALUE,
            SERVICE_NAME: "runpod-python-sdk",
            SERVICE_VERSION: runpod_version,
        }
    ),
)

span_processors: List[SpanExporter] = []

if RUNPOD_ENV.lower() == "local":
    span_processors.append(ConsoleSpanExporter())

if OTEL_COLLECTOR:
    span_processors.append(OTLPSpanExporter())

    trace.set_tracer_provider(otlp_provider)
    tracer = trace.get_tracer_provider()

    for span_processor in span_processors:
        tracer.add_span_processor(BatchSpanProcessor(span_processor))
        log.debug(f"Span processor: {span_processor}")

else:
    # Use NoOpTracerProvider to disable OTEL
    trace.set_tracer_provider(trace.NoOpTracerProvider())
    tracer = trace.get_tracer_provider()
    log.debug(f"No tracer is active")
