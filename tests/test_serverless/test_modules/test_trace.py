import unittest
from unittest.mock import patch, MagicMock
from aiohttp import TraceConfig
import asyncio
from runpod.serverless.modules.rp_trace import (
    on_request_start,
    on_request_chunk_sent,
    on_response_chunk_received,
    on_request_end,
    on_request_exception,
    on_dns_resolvehost_start,
    on_dns_resolvehost_end,
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

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_request_end(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        context.on_request_start = self.loop.time()
        context.on_dns_resolvehost_start = self.loop.time()
        context.on_dns_resolvehost_end = self.loop.time()
        context.on_connection_create_end = self.loop.time()

        self.loop.run_until_complete(on_request_end(session, context, params))
        mock_log.trace.assert_called()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_request_exception(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.exception = Exception("Test Exception")
        context.on_request_start = self.loop.time()

        self.loop.run_until_complete(on_request_exception(session, context, params))
        mock_log.debug.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_dns_resolvehost_start(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.host = 'test.com'
        context.on_request_start = self.loop.time()

        self.loop.run_until_complete(on_dns_resolvehost_start(session, context, params))
        assert hasattr(context, 'on_dns_resolvehost_start')
        mock_log.trace.assert_called_once()

    @patch('runpod.serverless.modules.rp_trace.log')
    def test_on_dns_resolvehost_end(self, mock_log):
        session = MagicMock()
        context = MagicMock()
        params = MagicMock()
        params.host = 'test.com'
        context.on_request_start = self.loop.time()

        self.loop.run_until_complete(on_dns_resolvehost_end(session, context, params))
        assert hasattr(context, 'on_dns_resolvehost_end')
        mock_log.trace.assert_called_once()
