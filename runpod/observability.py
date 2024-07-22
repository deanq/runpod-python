import json
import typing
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import (
    SpanExporter,
    SpanExportResult,
    BatchSpanProcessor, 
)
from opentelemetry import trace


class JSONSpanExporter(SpanExporter):
    def export(self, spans: typing.Sequence[ReadableSpan]):
        for span in spans:
            span_dict = {
                "name": span.name,
                "context": {
                    "trace_id": format(span.context.trace_id, '032x'),
                    "span_id": format(span.context.span_id, '016x'),
                    "trace_state": str(span.context.trace_state)
                },
                "parent_id": format(span.parent.span_id, '016x') if span.parent else None,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "attributes": {k: self._serialize_value(v) for k, v in span.attributes.items()},
                "events": [
                    {"name": e.name, "timestamp": e.timestamp, "attributes": {k: self._serialize_value(v) for k, v in e.attributes.items()}}
                    for e in span.events
                ],
                "status": {
                    "status_code": span.status.status_code.name,
                    "description": span.status.description
                },
                "kind": span.kind.name,
                "resource": {k: self._serialize_value(v) for k, v in span.resource.attributes.items()},
                "instrumentation_library": {
                    "name": span.instrumentation_info.name,
                    "version": span.instrumentation_info.version
                }
            }
            json_output = json.dumps(span_dict, indent=2)
            print(json_output)
        return SpanExportResult.SUCCESS

    def _serialize_value(self, value):
        """Helper method to ensure values are JSON serializable"""
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        if isinstance(value, (int, float, str, bool, type(None))):
            return value
        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        return str(value)

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
