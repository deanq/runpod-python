import json
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SpanExporter,
    SpanExportResult,
    BatchSpanProcessor, 
)
from opentelemetry import trace


class JSONSpanExporter(SpanExporter):
    def export(self, spans):
        for span in spans:
            print(vars(span))

        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        pass

   
# Set up OpenTelemetry
resource = Resource(attributes={"service.name": "runpod-python"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(JSONSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
