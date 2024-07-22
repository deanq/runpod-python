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
            # See opentelemetry.sdk.trace.ReadableSpan
            span_dict = {
                "name": span.name,
                "context": {
                    "trace_id": span.context.trace_id,
                    "span_id": span.context.span_id,
                    "trace_state": str(span.context.trace_state)
                },
                "parent_id": span.parent.span_id if span.parent else None,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "attributes": {k: v for k, v in span.attributes.items()},
                "events": [{
                    "name": e.name,
                    "timestamp": e.timestamp,
                    "attributes": e.attributes,
                    } for e in span.events],
                "status": {
                    "status_code": span.status.status_code,
                    "description": span.status.description,
                },
                "kind": span.kind.name,
                "resource": {k: v for k, v in span.resource.attributes.items()},
                "instrumentation_library": {
                    "name": span.instrumentation_info.name,
                    "version": span.instrumentation_info.version
                }
            }
            json_output = json.dumps(span_dict)
            print(json_output)

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
