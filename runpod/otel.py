import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import (
    Resource,
    SERVICE_NAME,
    SERVICE_NAMESPACE,
    SERVICE_INSTANCE_ID,
    SERVICE_VERSION,
    HOST_NAME,
)

RUNPOD_ENDPOINT_ID = "runpod.endpoint_id"
RUNPOD_POD_ID = "runpod.pod_id"

from runpod.version import __version__ as runpod_version


trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create(
            {
                "application": "runpod-serverless",
                SERVICE_NAME: "runpod-python-sdk",
                SERVICE_NAMESPACE: os.getenv("RUNPOD_ENDPOINT_ID"),
                RUNPOD_ENDPOINT_ID: os.getenv("RUNPOD_ENDPOINT_ID"),
                SERVICE_INSTANCE_ID: os.getenv("RUNPOD_POD_ID"),
                RUNPOD_POD_ID: os.getenv("RUNPOD_POD_ID"),
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
