"""
runpod | serverless | worker_loop.py
Called to convert a container into a worker pod for the runpod serverless platform.
"""
import os
import asyncio
from typing import Dict, Any

from runpod.http_client import AsyncClientSession
from runpod.serverless.modules import (
    rp_logger, rp_local, rp_handler, rp_ping,
    rp_scale
)
from .modules.rp_job import get_job, run_job, run_job_generator
from .modules.rp_http import send_result, stream_result
from .modules.worker_state import REF_COUNT_ZERO, JobsQueue
from .utils import rp_debugger

log = rp_logger.RunPodLogger()
heartbeat = rp_ping.Heartbeat()


def _is_local(config) -> bool:
    """ Returns True if the worker is running locally, False otherwise. """
    if config['rp_args'].get('test_input', None):
        return True

    if os.environ.get("RUNPOD_WEBHOOK_GET_JOB", None) is None:
        return True

    return False


def run_job(session, job_scaler, config):
    async def run_job_processor(job):
        is_stream = rp_handler.is_generator(config["handler"])
        if is_stream:
            generator_output = run_job_generator(config["handler"], job)
            log.debug("Handler is a generator, streaming results.", job['id'])

            job_result = {'output': []}
            async for stream_output in generator_output:
                log.debug(f"Stream output: {stream_output}", job['id'])
                if 'error' in stream_output:
                    job_result = stream_output
                    break
                if config.get('return_aggregate_stream', False):
                    job_result['output'].append(stream_output['output'])

                await stream_result(session, stream_output, job)
        else:
            job_result = await run_job(config["handler"], job)

        # If refresh_worker is set, pod will be reset after job is complete.
        if config.get("refresh_worker", False):
            log.info("refresh_worker flag set, stopping pod after job.", job['id'])
            job_result["stopPod"] = True
            job_scaler.kill_worker()

        # If rp_debugger is set, debugger output will be returned.
        if config["rp_args"].get("rp_debugger", False) and isinstance(job_result, dict):
            job_result["output"]["rp_debugger"] = rp_debugger.get_debugger_output()
            log.debug("rp_debugger | Flag set, returning debugger output.", job['id'])

            # Calculate ready delay for the debugger output.
            ready_delay = (config["reference_counter_start"] - REF_COUNT_ZERO) * 1000
            job_result["output"]["rp_debugger"]["ready_delay_ms"] = ready_delay
        else:
            log.debug("rp_debugger | Flag not set, skipping debugger output.", job['id'])
            rp_debugger.clear_debugger_output()

        # Send the job result to SLS
        await send_result(session, job_result, job, is_stream=is_stream)

    return run_job_processor


# ------------------------- Main Worker Running Loop ------------------------- #
async def run_worker(config: Dict[str, Any]) -> None:
    """
    Starts the worker loop for multi-processing.

    Args:
        config (Dict[str, Any]): Configuration parameters for the worker.
    """
    heartbeat.start_ping()

    client_session = AsyncClientSession()

    async with client_session as session:
        queue = JobsQueue()
        job_scaler = rp_scale.JobScaler()

        get_jobs = get_job(session, retry=True)
        run_jobs = run_job(session, job_scaler, config)
        
        await asyncio.gather(
            job_scaler.collector(get_jobs, queue),
            job_scaler.processor(run_jobs, queue),
        )


def main(config: Dict[str, Any]) -> None:
    """
    Checks if the worker is running locally or on RunPod.
    If running locally, the test job is run and the worker exits.
    If running on RunPod, the worker loop is created.
    """
    if _is_local(config):
        asyncio.run(rp_local.run_local(config))

    else:
        try:
            work_loop = asyncio.new_event_loop()
            asyncio.ensure_future(run_worker(config), loop=work_loop)
            work_loop.run_forever()

        finally:
            work_loop.close()
