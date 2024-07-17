import unittest
import json
from unittest.mock import patch, MagicMock, Mock
from aiohttp import TraceConfig
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

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_get_tracer(self, mock_log):
        assert isinstance(get_tracer(), TraceConfig)

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_request_start(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()

        self.loop.run_until_complete(on_request_start(session, context, params))
        assert hasattr(context, 'trace_id')
        assert hasattr(context, 'on_request_start')
        assert context.payload_size_bytes == 0
        assert context.response_size_bytes == 0
        mock_log.debug.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_connection_create_end(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.host = 'test.com'
        context.on_request_start = self.loop.time()

        self.loop.run_until_complete(on_connection_create_end(session, context, params))
        assert hasattr(context, 'on_connection_made')
        mock_log.debug.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_connection_reuseconn(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.host = 'test.com'
        context.on_request_start = self.loop.time()

        self.loop.run_until_complete(on_connection_reuseconn(session, context, params))
        assert hasattr(context, 'on_connection_made')
        mock_log.debug.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_request_chunk_sent(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.chunk = b'test data'
        context.on_request_start = self.loop.time()

        # Initial call to on_request_start to initialize context
        self.loop.run_until_complete(on_request_start(session, context, params))

        # Call on_request_chunk_sent multiple times to simulate multiple chunks being sent
        for _ in range(3):
            self.loop.run_until_complete(on_request_chunk_sent(session, context, params))
        
        # Verify that payload_size_bytes has accumulated
        assert context.payload_size_bytes == len(params.chunk) * 3
        mock_log.debug.assert_called()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_response_chunk_received(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.chunk = b'received data'
        context.on_request_start = self.loop.time()

        # Initial call to on_request_start to initialize context
        self.loop.run_until_complete(on_request_start(session, context, params))

        # Call on_response_chunk_received multiple times to simulate multiple chunks being received
        for _ in range(3):
            self.loop.run_until_complete(on_response_chunk_received(session, context, params))

        # Verify that payload_size_bytes has accumulated
        assert context.response_size_bytes == len(params.chunk) * 3
        mock_log.debug.assert_called()

    @patch('runpod.serverless.modules.rp_trace.report_trace')
    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_request_end(self, mock_log, mock_report_trace):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        context.on_request_start = self.loop.time()
        context.on_connection_made = self.loop.time()

        self.loop.run_until_complete(on_request_end(session, context, params))
        mock_log.trace.assert_not_called()
        mock_log.debug.assert_called_once()
        mock_report_trace.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.report_trace')
    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_request_exception(self, mock_log, mock_report_trace):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.exception = Exception("Test Exception")
        context.on_request_start = self.loop.time()

        self.loop.run_until_complete(on_request_exception(session, context, params))
        mock_log.trace.assert_not_called()
        mock_log.debug.assert_called_once()
        mock_report_trace.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_report_trace(self, mock_log):
        context = Mock()
        context.trace_id = "test-trace-id"
        context.on_connection_made = 0.5
        context.payload_size_bytes = 1024
        context.response_size_bytes = 2048

        params = Mock()
        params.method = "GET"
        params.url = "http://example.com"
        params.response = Mock()
        params.response.status = 200

        elapsed = 1.5

        report_trace(context, params, elapsed)

        expected_report = json.dumps({
            "traceId": "test-trace-id",
            "method": "GET",
            "url": "http://example.com",
            "connect": 500.0,  # 0.5 seconds to milliseconds
            "transfer": 1000.0,  # 1.5 - 0.5 seconds to milliseconds
            "total": 1500.0,  # 1.5 seconds to milliseconds
            "payload_size_bytes": 1024,
            "response_size_bytes": 2048,
            "response_status": 200
        })

        mock_log.trace.assert_called_once_with(expected_report)

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_report_trace_no_payload_or_response(self, mock_log):
        context = Mock()
        context.trace_id = "test-trace-id"
        context.on_connection_made = 0.5
        context.payload_size_bytes = None
        context.response_size_bytes = None

        params = Mock()
        params.method = "GET"
        params.url = "http://example.com"
        params.response = None

        elapsed = 1.5

        report_trace(context, params, elapsed)

        expected_report = json.dumps({
            "traceId": "test-trace-id",
            "method": "GET",
            "url": "http://example.com",
            "connect": 500.0,  # 0.5 seconds to milliseconds
            "transfer": 1000.0,  # 1.5 - 0.5 seconds to milliseconds
            "total": 1500.0,  # 1.5 seconds to milliseconds
        })

        mock_log.trace.assert_called_once_with(expected_report)

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_report_trace_with_response_status(self, mock_log):
        context = Mock()
        context.trace_id = "test-trace-id"
        context.on_connection_made = 0.5
        context.payload_size_bytes = None
        context.response_size_bytes = None

        params = Mock()
        params.method = "POST"
        params.url = "http://example.com/resource"
        params.response = Mock()
        params.response.status = 404

        elapsed = 2.0

        report_trace(context, params, elapsed)

        expected_report = json.dumps({
            "traceId": "test-trace-id",
            "method": "POST",
            "url": "http://example.com/resource",
            "connect": 500.0,  # 0.5 seconds to milliseconds
            "transfer": 1500.0,  # 2.0 - 0.5 seconds to milliseconds
            "total": 2000.0,  # 2.0 seconds to milliseconds
            "response_status": 404
        })

        mock_log.trace.assert_called_once_with(expected_report)
