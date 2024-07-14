# https://docs.aiohttp.org/en/stable/tracing_reference.html

import os
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
from .rp_logger import RunPodLogger


log = RunPodLogger()


async def on_request_start(session, context, params: TraceRequestStartParams):
    log.trace(f"on_request_start {params.method} {params.url}")
    context.on_request_start = session.loop.time()


async def on_request_chunk_sent(
    session, context, params: TraceRequestChunkSentParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_request_chunk_sent | {elapsed} ms")


async def on_response_chunk_received(
    session, context, params: TraceResponseChunkReceivedParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_response_chunk_received | {elapsed} ms")


async def on_request_end(session, context, params: TraceRequestEndParams):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_request_end | {elapsed} ms")

    elapsed = session.loop.time() - context.on_request_start
    context.on_request_end = elapsed

    dns_lookup = context.on_dns_resolvehost_end - context.on_dns_resolvehost_start
    connect = context.on_connection_create_end - dns_lookup
    transfer = elapsed - context.on_connection_create_end

    report = {
        "dns_lookup_and_dial": round(dns_lookup * 1000, 2),
        "connect": round(connect * 1000, 2),
        "transfer": round(transfer * 1000, 2),
        "total": round(elapsed * 1000, 2),
    }
    log.trace(report)


async def on_request_exception(
    session, context, params: TraceRequestExceptionParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_request_exception {params.exception} | {elapsed} ms")


async def on_request_redirect(
    session, context, params: TraceRequestRedirectParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_request_redirect {params.response.status} | {elapsed} ms")


async def on_connection_queued_start(
    session, context, params: TraceConnectionQueuedStartParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_connection_queued_start | {elapsed} ms")


async def on_connection_queued_end(
    session, context, params: TraceConnectionQueuedEndParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_connection_queued_end | {elapsed} ms")


async def on_connection_create_start(
    session, context, params: TraceConnectionCreateStartParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_connection_create_start | {elapsed} ms")


async def on_connection_create_end(
    session, context, params: TraceConnectionCreateEndParams
):
    elapsed = session.loop.time() - context.on_request_start
    context.on_connection_create_end = elapsed
    log.trace(f"on_connection_create_end | {elapsed} ms")


async def on_connection_reuseconn(
    session, context, params: TraceConnectionReuseconnParams
):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_connection_reuseconn | {elapsed} ms")


async def on_dns_resolvehost_start(
    session, context, params: TraceDnsResolveHostStartParams
):
    elapsed = session.loop.time() - context.on_request_start
    context.on_dns_resolvehost_start = elapsed
    log.trace(f"on_dns_resolvehost_start {params.host} | {elapsed} ms")


async def on_dns_resolvehost_end(
    session, context, params: TraceDnsResolveHostEndParams
):
    elapsed = session.loop.time() - context.on_request_start
    context.on_dns_resolvehost_end = elapsed
    log.trace(f"on_dns_resolvehost_end {params.host} | {elapsed} ms")


async def on_dns_cache_hit(session, context, params: TraceDnsCacheHitParams):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_dns_cache_hit {params.host} | {elapsed} ms")


async def on_dns_cache_miss(session, context, params: TraceDnsCacheMissParams):
    elapsed = session.loop.time() - context.on_request_start
    log.trace(f"on_dns_cache_miss {params.host} | {elapsed} ms")


def get_tracer() -> TraceConfig:
    trace_config = TraceConfig()

    if os.getenv("RUNPOD_TRACE"):
        log.trace("RUNPOD_TRACE is enabled")
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)
        trace_config.on_response_chunk_received.append(on_response_chunk_received)
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
        trace_config.on_response_chunk_received.append(on_response_chunk_received)
        trace_config.on_request_end.append(on_request_end)
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
