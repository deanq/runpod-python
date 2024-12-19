"""
    This module is used to handle HTTP requests.
"""

import json
import os

from aiohttp import ClientError
from aiohttp_retry import FibonacciRetry, RetryClient
from opentelemetry import trace

from runpod.http_client import ClientSession
from runpod.serverless.modules.rp_logger import RunPodLogger

from .worker_state import WORKER_ID

JOB_DONE_URL_TEMPLATE = str(
    os.environ.get("RUNPOD_WEBHOOK_POST_OUTPUT", "JOB_DONE_URL")
)
JOB_DONE_URL = JOB_DONE_URL_TEMPLATE.replace("$RUNPOD_POD_ID", WORKER_ID)

JOB_STREAM_URL_TEMPLATE = str(
    os.environ.get("RUNPOD_WEBHOOK_POST_STREAM", "JOB_STREAM_URL")
)
JOB_STREAM_URL = JOB_STREAM_URL_TEMPLATE.replace("$RUNPOD_POD_ID", WORKER_ID)

log = RunPodLogger()
tracer = trace.get_tracer(__name__)


@tracer.start_as_current_span("transmit", kind=trace.SpanKind.CLIENT)
async def _transmit(client_session: ClientSession, url, job_data):
    """
    Wrapper for transmitting results via POST.
    """
    span = trace.get_current_span()
    span.set_attribute("job_data", job_data)

    retry_options = FibonacciRetry(attempts=3)
    retry_client = RetryClient(
        client_session=client_session, retry_options=retry_options
    )

    kwargs = {
        "data": job_data,
        "headers": {
            "charset": "utf-8",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        "raise_for_status": True,
    }

    async with retry_client.post(url, **kwargs) as client_response:
        await client_response.text()


@tracer.start_as_current_span("handle_result", kind=trace.SpanKind.CLIENT)
async def _handle_result(
    session: ClientSession, job_data, job, url_template, log_message, is_stream=False
):
    """
    A helper function to handle the result, either for sending or streaming.
    """
    span = trace.get_current_span()
    span.set_attribute("request_id", job.get("id"))
    span.set_attribute("is_stream", is_stream)

    try:
        serialized_job_data = json.dumps(job_data, ensure_ascii=False)

        is_stream = "true" if is_stream else "false"
        url = url_template.replace("$ID", job["id"]) + f"&isStream={is_stream}"

        await _transmit(session, url, serialized_job_data)
        log.debug(f"{log_message}", job["id"])

    except ClientError as err:
        span.record_exception(err)
        log.error(f"Failed to return job results. | {err}", job["id"])

    except (TypeError, RuntimeError) as err:
        span.record_exception(err)
        log.error(f"Error while returning job result. | {err}", job["id"])

    finally:
        # job_data status is used for local development with FastAPI
        if (
            url_template == JOB_DONE_URL
            and job_data.get("status", None) != "IN_PROGRESS"
        ):
            log.info("Finished.", job["id"])


@tracer.start_as_current_span("send_result")
async def send_result(session, job_data, job, is_stream=False):
    """
    Return the job results.
    """
    await _handle_result(
        session, job_data, job, JOB_DONE_URL, "Results sent.", is_stream=is_stream
    )


@tracer.start_as_current_span("stream_result")
async def stream_result(session, job_data, job):
    """
    Return the stream job results.
    """
    await _handle_result(
        session, job_data, job, JOB_STREAM_URL, "Intermediate results sent."
    )
