"""
runpod | serverless | worker_loop.py
Called to convert a container into a worker pod for the runpod serverless platform.
"""
import os
import asyncio
from typing import Dict, Any

from runpod.http_client import AsyncClientSession, ClientSession
from runpod.serverless.modules import (
    rp_logger, rp_local, rp_handler, rp_ping,
    rp_scale
)
from .modules.rp_job import run_job, run_job_generator, get_job
from .modules.rp_http import send_result, stream_result
from .modules.worker_state import REF_COUNT_ZERO
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


async def _process_job(job, session: ClientSession, job_scaler: rp_scale.JobScaler, config):
    if rp_handler.is_generator(config["handler"]):
        is_stream = True
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
        is_stream = False
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


def run_scheduled_job(session, job_scaler: rp_scale.JobScaler, config):
    async def run_job_processor(job):
        return await _process_job(job, session, job_scaler, config)
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
        job_scaler = rp_scale.JobScaler(
            concurrency_modifier=config.get('concurrency_modifier', None)
        )

        while job_scaler.is_alive():

            async for job in job_scaler.get_jobs(session):
                # Process the job here
                asyncio.create_task(_process_job(job, session, job_scaler, config))

                # Allow job processing
                await asyncio.sleep(0)

            await asyncio.sleep(0)

        # Stops the worker loop if the kill_worker flag is set.
        asyncio.get_event_loop().stop()


async def run_scheduler(config: Dict[str, Any]) -> None:
    """
    Starts the worker loop for multi-processing.

    Args:
        config (Dict[str, Any]): Configuration parameters for the worker.
    """
    heartbeat.start_ping()

    client_session = AsyncClientSession()

    async with client_session as session:
        job_scheduler = rp_scale.JobScheduler()
        get_jobs = get_job(session)
        run_jobs = run_scheduled_job(session, job_scheduler, config)
        await asyncio.create_task(job_scheduler.run(get_jobs, run_jobs))


async def run_scheduler(config: Dict[str, Any]) -> None:
    heartbeat.start_ping()

    if _is_local(config):
        await rp_local.run_local(config)

    else:
        if os.getenv('RUNPOD_DEANQ', False):
            await run_scheduler(config)
        else:
            await run_worker(config)


def main(config: Dict[str, Any]) -> None:
    asyncio.run(run_scheduler(config))
