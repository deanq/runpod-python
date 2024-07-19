import unittest
import json
from types import SimpleNamespace
from time import time
from unittest.mock import patch, MagicMock
from aiohttp import (
    TraceConfig,
    TraceRequestStartParams,
    TraceConnectionCreateEndParams,
    TraceConnectionReuseconnParams,
    TraceRequestExceptionParams,
    TraceRequestChunkSentParams,
    TraceResponseChunkReceivedParams,
)
import asyncio
from runpod.serverless.modules.rp_trace import (
    on_request_start,
    on_connection_create_end,
    on_connection_reuseconn,
    on_request_chunk_sent,
    on_response_chunk_received,
    on_request_end,
    on_request_exception,
    report_trace,
    get_tracer,
)


class TestRPTrace(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_get_tracer(self):
        assert isinstance(get_tracer(), TraceConfig)

    def test_on_request_start(self):
        session = MagicMock()
        context = SimpleNamespace()
        params = TraceRequestStartParams("GET", "http://test.com/", { "x-request-id": "myRequestId" })

        self.loop.run_until_complete(on_request_start(session, context, params))
        assert hasattr(context, 'on_request_start')
        assert hasattr(context, 'trace_id')
        assert context.method == params.method
        assert context.url == params.url

    def test_on_connection_create_end(self):
        session = MagicMock()
        context = SimpleNamespace(on_request_start=self.loop.time())
        params = TraceConnectionCreateEndParams()

        self.loop.run_until_complete(on_connection_create_end(session, context, params))

    def test_on_connection_reuseconn(self):
        session = MagicMock()
        context = SimpleNamespace(on_request_start=self.loop.time())
        params = TraceConnectionReuseconnParams()

        self.loop.run_until_complete(on_connection_reuseconn(session, context, params))

    def test_on_request_chunk_sent(self):
        session = MagicMock()
        context = SimpleNamespace(on_request_start=self.loop.time())
        params = TraceRequestChunkSentParams("GET", "http://test.com/", chunk=b'test data')

        # Initial call to on_request_start to initialize context
        self.loop.run_until_complete(on_request_start(session, context, params))

        # Call on_request_chunk_sent multiple times to simulate multiple chunks being sent
        for _ in range(3):
            self.loop.run_until_complete(on_request_chunk_sent(session, context, params))
        
        # Verify that payload_size_bytes has accumulated
        assert context.payload_size_bytes == len(params.chunk) * 3

    def test_on_response_chunk_received(self):
        session = MagicMock()
        context = SimpleNamespace(on_request_start=self.loop.time())
        params = TraceResponseChunkReceivedParams("GET", "http://test.com/", chunk=b'received data')

        # Initial call to on_request_start to initialize context
        self.loop.run_until_complete(on_request_start(session, context, params))

        # Call on_response_chunk_received multiple times to simulate multiple chunks being received
        for _ in range(3):
            self.loop.run_until_complete(on_response_chunk_received(session, context, params))

        # Verify that payload_size_bytes has accumulated
        assert context.response_size_bytes == len(params.chunk) * 3

    @patch('runpod.serverless.modules.rp_trace.report_trace')
    def test_on_request_end(self, mock_report_trace):
        session = MagicMock()
        context = SimpleNamespace(on_request_start=self.loop.time())
        params = MagicMock()

        self.loop.run_until_complete(on_request_end(session, context, params))
        mock_report_trace.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.report_trace')
    def test_on_request_exception(self, mock_report_trace):
        session = MagicMock()
        context = SimpleNamespace(on_request_start=self.loop.time())
        params = TraceRequestExceptionParams("GET", "http://test.com/", headers={}, exception=Exception("Test Exception"))

        self.loop.run_until_complete(on_request_exception(session, context, params))
        mock_report_trace.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_report_trace(self, mock_log):
        context = SimpleNamespace()
        context.trace_id = "test-trace-id"
        context.on_request_start = time()
        context.connect = 0.5
        context.payload_size_bytes = 1024
        context.response_size_bytes = 2048
        context.retries = 0

        params = MagicMock()
        params.response.status = 200

        elapsed = 1.5

        expected_report = json.dumps({
            "trace_id": "test-trace-id",
            "connect": 500.0,
            "payload_size_bytes": 1024,
            "response_size_bytes": 2048,
            "retries": 0,
            "transfer": 1000.0,  # 1.5 - 0.5 seconds to milliseconds
            "total": 1500.0,  # 1.5 seconds to milliseconds
            "response_status": 200
        })

        report_trace(context, params, elapsed, mock_log.trace)
        mock_log.trace.assert_called_once_with(expected_report)

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_report_trace_error_log(self, mock_log):
        context = SimpleNamespace()
        context.trace_id = "test-trace-id"
        context.on_request_start = time()
        context.connect = 0.5
        context.retries = 3

        params = MagicMock()
        params.response.status = 502

        elapsed = 1.5

        expected_report = json.dumps({
            "trace_id": "test-trace-id",
            "connect": 500.0,
            "retries": 3,
            "transfer": 1000.0,  # 1.5 - 0.5 seconds to milliseconds
            "total": 1500.0,  # 1.5 seconds to milliseconds
            "response_status": 502
        })

        report_trace(context, params, elapsed, mock_log.error)
        mock_log.error.assert_called_once_with(expected_report)
