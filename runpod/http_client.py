import aiohttp
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.aiohttp_client import create_trace_config


class AsyncClientSession(aiohttp.ClientSession):
    _tracing_initialized = False

    def __init__(self, *args, **kwargs):
        if not AsyncClientSession._tracing_initialized:
            self._init_tracing()
            AsyncClientSession._tracing_initialized = True
        
        trace_config = create_trace_config()
        if 'trace_configs' in kwargs:
            kwargs['trace_configs'].append(trace_config)
        else:
            kwargs['trace_configs'] = [trace_config]

        super().__init__(*args, **kwargs)

    @staticmethod
    def _init_tracing():
        trace.set_tracer_provider(TracerProvider())
        console_exporter = ConsoleSpanExporter()
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(console_exporter)
        )
