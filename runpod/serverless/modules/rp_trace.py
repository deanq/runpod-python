# https://docs.aiohttp.org/en/stable/tracing_reference.html

import os
import asyncio
from aiohttp import (
    TraceConfig,
    TraceRequestStartParams,
    TraceRequestEndParams,
    TraceRequestExceptionParams,
    TraceConnectionQueuedStartParams,
    TraceConnectionQueuedEndParams,
    TraceConnectionCreateStartParams,
    TraceConnectionCreateEndParams,
    TraceConnectionReuseconnParams,
    TraceDnsResolveHostStartParams,
    TraceDnsResolveHostEndParams,
    TraceDnsCacheHitParams,
    TraceDnsCacheMissParams,
    TraceRequestRedirectParams,
    TraceRequestChunkSentParams,
    TraceResponseChunkReceivedParams,
)
from uuid import uuid4
from .rp_logger import RunPodLogger


log = RunPodLogger()


async def on_request_start(session, context, params: TraceRequestStartParams):
    context.trace_id = str(uuid4())
    log.trace(f"{context.trace_id} | on_request_start")
    context.on_request_start = asyncio.get_event_loop().time()
    context.payload_size_bytes = 0


async def on_request_chunk_sent(
    session, context, params: TraceRequestChunkSentParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.payload_size_bytes += len(params.chunk)
    log.trace(f"{context.trace_id} | on_request_chunk_sent | {elapsed*1000:.1f} ms")


async def on_response_chunk_received(
    session, context, params: TraceResponseChunkReceivedParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_response_chunk_received | {elapsed*1000:.1f} ms")


async def on_request_end(session, context, params: TraceRequestEndParams):
    log.debug(session, context)
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_request_end | {elapsed*1000:.1f} ms")

    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.on_request_end = elapsed

    dns_lookup = context.on_dns_resolvehost_end - context.on_dns_resolvehost_start
    connect = context.on_connection_create_end - dns_lookup
    transfer = elapsed - context.on_connection_create_end

    report = {
        "trace_id": context.trace_id,
        "method": params.method,
        "url": f"{params.url}",
        "payload_size_bytes": context.payload_size_bytes,
        "dns_lookup": round(dns_lookup * 1000, 1),
        "connect": round(connect * 1000, 1),
        "transfer": round(transfer * 1000, 1),
        "total": round(elapsed * 1000, 1),
    }
    log.trace(report)


async def on_request_exception(
    session, context, params: TraceRequestExceptionParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_request_exception {params.exception} | {elapsed*1000:.1f} ms")


async def on_request_redirect(
    session, context, params: TraceRequestRedirectParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_request_redirect {params.response.status} | {elapsed*1000:.1f} ms")


async def on_connection_queued_start(
    session, context, params: TraceConnectionQueuedStartParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_connection_queued_start | {elapsed*1000:.1f} ms")


async def on_connection_queued_end(
    session, context, params: TraceConnectionQueuedEndParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_connection_queued_end | {elapsed*1000:.1f} ms")


async def on_connection_create_start(
    session, context, params: TraceConnectionCreateStartParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_connection_create_start | {elapsed*1000:.1f} ms")


async def on_connection_create_end(
    session, context, params: TraceConnectionCreateEndParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.on_connection_create_end = elapsed
    log.trace(f"{context.trace_id} | on_connection_create_end | {elapsed*1000:.1f} ms")


async def on_connection_reuseconn(
    session, context, params: TraceConnectionReuseconnParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_connection_reuseconn | {elapsed*1000:.1f} ms")


async def on_dns_resolvehost_start(
    session, context, params: TraceDnsResolveHostStartParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.on_dns_resolvehost_start = elapsed
    log.trace(f"{context.trace_id} | on_dns_resolvehost_start ({params.host}) | {elapsed*1000:.1f} ms")


async def on_dns_resolvehost_end(
    session, context, params: TraceDnsResolveHostEndParams
):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    context.on_dns_resolvehost_end = elapsed
    log.trace(f"{context.trace_id} | on_dns_resolvehost_end ({params.host}) | {elapsed*1000:.1f} ms")


async def on_dns_cache_hit(session, context, params: TraceDnsCacheHitParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_dns_cache_hit ({params.host}) | {elapsed*1000:.1f} ms")


async def on_dns_cache_miss(session, context, params: TraceDnsCacheMissParams):
    elapsed = asyncio.get_event_loop().time() - context.on_request_start
    log.trace(f"{context.trace_id} | on_dns_cache_miss ({params.host}) | {elapsed*1000:.1f} ms")


def get_tracer() -> TraceConfig:
    trace_config = TraceConfig()

    if os.getenv("RUNPOD_TRACE"):
        log.trace("RUNPOD_TRACE is enabled")
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)
        trace_config.on_response_chunk_received.append(on_response_chunk_received)
        trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
        trace_config.on_request_exception.append(on_request_exception)
        trace_config.on_request_redirect.append(on_request_redirect)
        trace_config.on_connection_queued_start.append(on_connection_queued_start)
        trace_config.on_connection_queued_end.append(on_connection_queued_end)
        trace_config.on_connection_create_start.append(on_connection_create_start)
        trace_config.on_connection_create_end.append(on_connection_create_end)
        trace_config.on_connection_reuseconn.append(on_connection_reuseconn)
        trace_config.on_dns_resolvehost_start.append(on_dns_resolvehost_start)
        trace_config.on_dns_resolvehost_end.append(on_dns_resolvehost_end)
        trace_config.on_dns_cache_hit.append(on_dns_cache_hit)
        trace_config.on_dns_cache_miss.append(on_dns_cache_miss)

    return trace_config
