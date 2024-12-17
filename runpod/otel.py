import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import (
    Resource,
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME,
    SERVICE_VERSION,
)
from runpod.version import __version__ as runpod_version


def start():
    OTEL_COLLECTOR = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    OTEL_SAMPLING_RATE = float(os.getenv("OTEL_SAMPLING_RATE", "0.01"))

    RUNPOD_ENV = os.getenv("ENV", "local").lower()
    RUNPOD_LOG_LEVEL = os.getenv("RUNPOD_LOG_LEVEL", "").lower()

    RUNPOD_ENDPOINT_ID = "runpod.endpoint_id"
    RUNPOD_ENDPOINT_ID_VALUE = os.getenv("RUNPOD_ENDPOINT_ID", "")
    RUNPOD_POD_ID = "runpod.pod_id"
    RUNPOD_POD_ID_VALUE = os.getenv("RUNPOD_POD_ID", "")

    if RUNPOD_LOG_LEVEL == "trace":
        sampler = sampling.ALWAYS_ON
    else:
        sampler = sampling.TraceIdRatioBased(OTEL_SAMPLING_RATE)

    tracer = TracerProvider(
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

    if OTEL_COLLECTOR:
        tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tracer)
        print(f"OpenTelemetry is on: {sampler.get_description()}")

    elif RUNPOD_ENV == "local":
        tracer.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(tracer)
        print(f"Console tracing is on: {sampler.get_description()}")

    else:
        # Use NoOpTracerProvider to disable OTEL
        trace.set_tracer_provider(trace.NoOpTracerProvider())
