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
from .rp_logger import RunPodLogger


log = RunPodLogger()

# https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

# https://opentelemetry.io/docs/languages/sdk-configuration/general/#otel_service_name
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "serverless-worker")

OTEL_SAMPLING_RATE = float(os.getenv("OTEL_SAMPLING_RATE", "0.01"))


def start(
    service_name: str = OTEL_SERVICE_NAME,
    collector: str = OTEL_EXPORTER_OTLP_ENDPOINT,
    rate: float = OTEL_SAMPLING_RATE,
):
    """
    Initializes the OpenTelemetry global tracer provider.

    Args:
        service_name: The service name to associate with the OTEL spans.
        collector: The URL of the OTEL collector to report to. Defaults to
            the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable.
        rate: The sampling rate between 0.0 and 1.0. Defaults to the
            `OTEL_SAMPLING_RATE` env var or 0.01 (1%)

    Notes:
        The env var `RUNPOD_LOG_LEVEL=trace` can be set to force mandatory tracing.
        Otherwise, the sampling rate is used to control the amount of tracing.

        If a collector is provided, the traces are exported to it.
        Else if the environment is "local", the traces are printed to the console.

        If neither of the above conditions are met, then tracing is disabled.
    """
    RUNPOD_ENV = get_deployment_env()
    RUNPOD_LOG_LEVEL = os.getenv("RUNPOD_LOG_LEVEL", "").lower()

    if RUNPOD_LOG_LEVEL == "trace":
        sampler = sampling.ALWAYS_ON
    else:
        sampler = sampling.TraceIdRatioBased(rate)

    tracer = TracerProvider(
        sampler=sampler,
        resource=get_resource(service_name, RUNPOD_ENV),
    )

    if collector:
        tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tracer)
        log.info(f"OpenTelemetry is on: {sampler.get_description()}")

    elif RUNPOD_ENV == "local":
        tracer.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(tracer)
        log.info(f"Tracing prints to console: {sampler.get_description()}")

    else:
        # Use NoOpTracerProvider to disable OTEL
        trace.set_tracer_provider(trace.NoOpTracerProvider())


def get_resource(service_name: str, environment: str) -> Resource:
    """
    Constructs and returns a Resource object for OpenTelemetry.

    The Resource object includes essential metadata such as deployment
    environment, service name, service version, and unique identifiers
    for the RunPod endpoint and pod.

    Args:
        service_name: The name of the service to associate with the resource.
        environment: The deployment environment (e.g., dev, prod, local).

    Returns:
        A Resource object containing metadata for tracing and monitoring.
    """
    RUNPOD_ENDPOINT_ID = "runpod.endpoint_id"
    RUNPOD_ENDPOINT_ID_VALUE = os.getenv("RUNPOD_ENDPOINT_ID", "")
    RUNPOD_POD_ID = "runpod.pod_id"
    RUNPOD_POD_ID_VALUE = os.getenv("RUNPOD_POD_ID", "")

    return Resource.create(
        {
            DEPLOYMENT_ENVIRONMENT: environment,
            RUNPOD_ENDPOINT_ID: RUNPOD_ENDPOINT_ID_VALUE,
            RUNPOD_POD_ID: RUNPOD_POD_ID_VALUE,
            SERVICE_NAME: service_name,
            SERVICE_VERSION: runpod_version,
        }
    )


def get_deployment_env() -> str:
    RUNPOD_API_URL = os.getenv("RUNPOD_WEBHOOK_PING", "")
    if "runpod.dev" in RUNPOD_API_URL:
        return "dev"
    if "runpod.ai" in RUNPOD_API_URL:
        return "prod"
    return "local"
