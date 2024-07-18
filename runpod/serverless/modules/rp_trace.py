# https://docs.aiohttp.org/en/stable/tracing_reference.html

import asyncio
import json
import types
from aiohttp import (
    TraceConfig,
    TraceRequestStartParams,
    TraceConnectionCreateEndParams,
    TraceConnectionReuseconnParams,
    TraceRequestEndParams,
    TraceRequestExceptionParams,
    TraceRequestChunkSentParams,
    TraceResponseChunkReceivedParams,
)
from uuid import uuid4
from .rp_logger import RunPodLogger


log = RunPodLogger()


async def on_request_start(session, context, params: TraceRequestStartParams):
    context.on_request_start = asyncio.get_event_loop().time()
    context.trace_id = str(uuid4())
    context.method = params.get("method")
    context.url = params.get("url")

    log.trace(f"on_request_start | headers: {params.get('headers')}")

    if hasattr(context, "trace_request_ctx"):
        context.retries = context.trace_request_ctx.get("current_attempt", 0)


async def on_connection_create_end(session, context, params: TraceConnectionCreateEndParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.connect = round(elapsed * 1000, 1)


async def on_connection_reuseconn(session, context, params: TraceConnectionReuseconnParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.connect = round(elapsed * 1000, 1)


async def on_request_chunk_sent(session, context, params: TraceRequestChunkSentParams):
    if not hasattr(context, "payload_size_bytes"):
        context.payload_size_bytes = 0
    context.payload_size_bytes += len(params.chunk)


async def on_response_chunk_received(session, context, params: TraceResponseChunkReceivedParams):
    if not hasattr(context, "response_size_bytes"):
        context.response_size_bytes = 0
    context.response_size_bytes += len(params.chunk)


async def on_request_end(session, context, params: TraceRequestEndParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    # log to trace level
    report_trace(context, params, elapsed)


async def on_request_exception(session, context, params: TraceRequestExceptionParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    # log to error level
    report_trace(context, params, elapsed, log.error)


def report_trace(context: types.SimpleNamespace, params, elapsed, logger=log.trace):
    context.transfer = round((elapsed - context.connect) * 1000, 1)
    context.connect = round(context.connect * 1000, 1)
    context.total = round(elapsed * 1000, 1)
    delattr(context, 'on_request_start')

    if hasattr(params, 'response') and params.response:
        context.response_status = params.response.status

    logger(json.dumps(vars(context)))


def get_tracer() -> TraceConfig:
    trace_config = TraceConfig()

    trace_config.on_request_start.append(on_request_start)
    trace_config.on_connection_create_end.append(on_connection_create_end)
    trace_config.on_connection_reuseconn.append(on_connection_reuseconn)
    trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
    trace_config.on_response_chunk_received.append(on_response_chunk_received)
    trace_config.on_request_end.append(on_request_end)
    trace_config.on_request_exception.append(on_request_exception)

    return trace_config
