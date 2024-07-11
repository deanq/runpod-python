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


async def on_request_start(session, trace_config_ctx, params: TraceRequestStartParams):
    log.trace(f"on_request_start {params.method} {params.url}")


async def on_request_chunk_sent(
    session, trace_config_ctx, params: TraceRequestChunkSentParams
):
    log.trace(f"on_request_chunk_sent {params.method} {params.url}")


async def on_response_chunk_received(
    session, trace_config_ctx, params: TraceResponseChunkReceivedParams
):
    log.trace(f"on_response_chunk_received {params.method} {params.url}")


async def on_request_end(session, trace_config_ctx, params: TraceRequestEndParams):
    log.trace(f"on_request_end {params.method} {params.url}")


async def on_request_exception(
    session, trace_config_ctx, params: TraceRequestExceptionParams
):
    log.trace(f"on_request_exception {params.method} {params.url} {params.exception}")


async def on_request_redirect(
    session, trace_config_ctx, params: TraceRequestRedirectParams
):
    log.trace(f"on_request_redirect {params.response.status} {params.response.url}")


async def on_connection_queued_start(
    session, trace_config_ctx, params: TraceConnectionQueuedStartParams
):
    log.trace(f"on_connection_queued_start")


async def on_connection_queued_end(
    session, trace_config_ctx, params: TraceConnectionQueuedEndParams
):
    log.trace(f"on_connection_queued_end")


async def on_connection_create_start(
    session, trace_config_ctx, params: TraceConnectionCreateStartParams
):
    log.trace(f"on_connection_create_start")


async def on_connection_create_end(
    session, trace_config_ctx, params: TraceConnectionCreateEndParams
):
    log.trace(f"on_connection_create_end")


async def on_connection_reuseconn(
    session, trace_config_ctx, params: TraceConnectionReuseconnParams
):
    log.trace(f"on_connection_reuseconn")


async def on_dns_resolvehost_start(
    session, trace_config_ctx, params: TraceDnsResolveHostStartParams
):
    log.trace(f"on_dns_resolvehost_start {params.host}")


async def on_dns_resolvehost_end(
    session, trace_config_ctx, params: TraceDnsResolveHostEndParams
):
    log.trace(f"on_dns_resolvehost_end {params.host}")


async def on_dns_cache_hit(session, trace_config_ctx, params: TraceDnsCacheHitParams):
    log.trace(f"on_dns_cache_hit {params.host}")


async def on_dns_cache_miss(session, trace_config_ctx, params: TraceDnsCacheMissParams):
    log.trace(f"on_dns_cache_miss {params.host}")


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
