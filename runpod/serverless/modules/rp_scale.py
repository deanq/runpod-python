'''
runpod | serverless | rp_scale.py
Provides the functionality for scaling the runpod serverless worker.
'''

import asyncio
from typing import Any, Dict

from ...http_client import ClientSession
from ..utils import rp_debugger
from .rp_handler import is_generator
from .rp_http import send_result, stream_result
from .rp_job import get_job, run_job, run_job_generator
from .rp_logger import RunPodLogger
from .worker_state import JobsQueue, REF_COUNT_ZERO

log = RunPodLogger()
job_list = JobsQueue()


def _default_concurrency_modifier(current_concurrency: int) -> int:
    """
    Default concurrency modifier.

    This function returns the current concurrency without any modification.

    Args:
        current_concurrency (int): The current concurrency.

    Returns:
        int: The current concurrency.
    """
    return current_concurrency


class JobScaler():
    """
    Job Scaler. This class is responsible for scaling the number of concurrent requests.
    """

    def __init__(self, concurrency_modifier: Any):
        if concurrency_modifier is None:
            self.concurrency_modifier = _default_concurrency_modifier
        else:
            self.concurrency_modifier = concurrency_modifier

        self.current_concurrency = 1
        self._is_alive = True

    def is_alive(self):
        """
        Return whether the worker is alive or not.
        """
        return self._is_alive

    def kill_worker(self):
        """
        Whether to kill the worker.
        """
        log.debug("kill worker")
        self._is_alive = False

    async def get_jobs(self, session: ClientSession, timeout: int = 60):
        """
        Acquire multiple jobs from the API and add them to the jobs queue.

        Runs the block in an infinite loop while the worker is alive.

        Stops if jobs are not acquired within the timeout period (seconds).
        """
        start_time = asyncio.get_event_loop().time()

        while self.is_alive():
            self.current_concurrency = self.concurrency_modifier(self.current_concurrency)
            log.debug(f"Concurrency set to: {self.current_concurrency}")

            log.debug(f"Jobs in progress: {job_list.get_job_count()}")

            jobs_needed = self.current_concurrency - job_list.get_job_count()

            if jobs_needed > 0:
                acquired_jobs = await get_job(session, jobs_needed)

                if acquired_jobs:
                    for job in acquired_jobs:
                        await job_list.add_job(job)
                    log.debug(f"Acquired {len(acquired_jobs)} jobs.")
                    start_time = asyncio.get_event_loop().time()  # Reset the start time

                else:
                    log.debug("No jobs acquired, backing off.")
                    await asyncio.sleep(10)  # Back off if no jobs were acquired

            else:
                log.debug("No more jobs needed, waiting for the next cycle.")
                await asyncio.sleep(5)  # yield control if no jobs are needed

            # Check if the timeout has been exceeded
            if asyncio.get_event_loop().time() - start_time > timeout:
                log.debug(f"Timeout of {timeout} seconds reached, stopping job scaler.")
                self.kill_worker()  # Stop the worker
                break

            await asyncio.sleep(0)  # yield control back to the event loop

    async def run_jobs(self, session: ClientSession, config: Dict[str, Any]):
        """
        Retrieve jobs from the jobs queue and process them.

        Runs the block in an infinite loop while the worker is alive or jobs queue is not empty.
        """
        while self.is_alive() or not job_list.empty():
            job = await job_list.get_job()

            try:
                log.debug(f"Processing job: {job}")

                if is_generator(config["handler"]):
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
                    self.kill_worker()

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

            # pylint: disable=broad-exception-raised
            except Exception as e:
                print(f"Exception occurred while processing job {job}: {e}")

            finally:
                job_list.task_done()
                log.debug(f"Job completed: {job}")

            await asyncio.sleep(0)  # yield control back to the event loop
