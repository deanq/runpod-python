# https://docs.aiohttp.org/en/stable/tracing_reference.html

import os
import asyncio
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
from .rp_logger import RunPodLogger, LOG_LEVELS


log = RunPodLogger()


async def on_request_start(session, context, params: TraceRequestStartParams):
    context.trace_id = str(uuid4())
    context.on_request_start = asyncio.get_event_loop().time()
    context.payload_size_bytes = 0
    context.response_size_bytes = 0
    log.debug(f"{context.trace_id} | on_request_start")


async def on_connection_create_end(session, context, params: TraceConnectionCreateEndParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.on_connection_made = elapsed
    log.debug(f"{context.trace_id} | on_connection_create_end | {elapsed*1000:.1f} ms")


async def on_connection_reuseconn(session, context, params: TraceConnectionReuseconnParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.on_connection_made = elapsed
    log.debug(f"{context.trace_id} | on_connection_reuseconn | {elapsed*1000:.1f} ms")


async def on_request_chunk_sent(session, context, params: TraceRequestChunkSentParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.payload_size_bytes += len(params.chunk)
    log.debug(f"{context.trace_id} | on_request_chunk_sent | {elapsed*1000:.1f} ms")


async def on_response_chunk_received(session, context, params: TraceResponseChunkReceivedParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.response_size_bytes += len(params.chunk)
    log.debug(f"{context.trace_id} | on_response_chunk_received | {elapsed*1000:.1f} ms")


async def on_request_end(session, context, params: TraceRequestEndParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.debug(f"{context.trace_id} | on_request_end | {elapsed*1000:.1f} ms")
    report_trace(context, params, elapsed)


async def on_request_exception(session, context, params: TraceRequestExceptionParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.debug(f"{context.trace_id} | on_request_exception {params.exception} | {elapsed*1000:.1f} ms")
    report_trace(context, params, elapsed)


def report_trace(context, params, elapsed):
    connect = context.on_connection_made
    transfer = elapsed - context.on_connection_made

    report = {
        "trace_id": context.trace_id,
        "method": params.method,
        "url": f"{params.url}",
        "connect": round(connect * 1000, 1),
        "transfer": round(transfer * 1000, 1),
        "total": round(elapsed * 1000, 1),
    }

    if context.payload_size_bytes:
        report["payload_size_bytes"] = context.payload_size_bytes

    if context.response_size_bytes:
        report["response_size_bytes"] = context.response_size_bytes

    if hasattr(params, 'response') and params.response:
        report["response_status"] = params.response.status

    log.trace(report)


def get_tracer() -> TraceConfig:
    trace_config = TraceConfig()
    log_level = os.getenv("RUNPOD_LOG_LEVEL")

    if log_level == "TRACE" or log_level == LOG_LEVELS.index("TRACE"):
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_connection_create_end.append(on_connection_create_end)
        trace_config.on_connection_reuseconn.append(on_connection_reuseconn)
        trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
        trace_config.on_response_chunk_received.append(on_response_chunk_received)
        trace_config.on_request_end.append(on_request_end)
        trace_config.on_request_exception.append(on_request_exception)

    return trace_config
