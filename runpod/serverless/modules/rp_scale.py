'''
runpod | serverless | rp_scale.py
Provides the functionality for scaling the runpod serverless worker.
'''

import asyncio
import typing

from runpod.serverless.modules.rp_logger import RunPodLogger
from .rp_job import get_job
from .worker_state import Jobs, JobsQueue

log = RunPodLogger()
job_list = Jobs()


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

    def __init__(self, concurrency_modifier: typing.Any):
        if concurrency_modifier is None:
            self.concurrency_modifier = _default_concurrency_modifier
        else:
            self.concurrency_modifier = concurrency_modifier

        self.background_get_job_tasks = set()
        self.job_history = []
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
        self._is_alive = False

    async def get_jobs(self, session):
        """
        Retrieve multiple jobs from the server in parallel using concurrent requests.

        Returns:
            List[Any]: A list of job data retrieved from the server.
        """
        while self.is_alive():
            self.current_concurrency = self.concurrency_modifier(self.current_concurrency)
            log.debug(f"Concurrency set to: {self.current_concurrency}")

            log.debug(f"Jobs in progress: {job_list.get_job_count()}")
            if job_list.get_job_count() < self.current_concurrency and self.is_alive():
                log.debug("Job list is less than concurrency, getting more jobs.")

                tasks = [
                    asyncio.create_task(get_job(session, retry=False))
                    for _ in range(self.current_concurrency if job_list.get_job_list() else 1)
                ]

                for job_future in asyncio.as_completed(tasks):
                    job = await job_future
                    self.job_history.append(1 if job else 0)
                    if job:
                        yield job

            await asyncio.sleep(0)


class JobScheduler(JobScaler):
    """
    Job Scaler. This class is responsible for scaling the number of concurrent requests.
    """

    def __init__(self):
        self._is_alive = True
        self.queue = JobsQueue()

    def is_alive(self):
        """
        Return whether the worker is alive or not.
        """
        return self._is_alive

    def kill_worker(self):
        """
        Whether to kill the worker.
        """
        self._is_alive = False

    async def collector(self, collectorFn: typing.Coroutine):
        """
        Retrieve jobs from the server and add them to the queue.

        This function runs in a loop, waiting for jobs to be received from the server.
        If a job is received, it is added to the queue for processing.
        The loop waits for 1 second before fetching jobs again.
        
        Args:
            collectorFn (typing.Coroutine): The coroutine function used to get jobs from the server.
        """
        while self.is_alive():
            log.debug(f"Jobs in progress: {self.queue.get_job_count()}")
            if job := await collectorFn():
                log.debug(f"Job received {job}")
                await self.queue.add_job(job)
            # Wait for 1 second before fetching jobs again
            await asyncio.sleep(1)

    async def processor(self, processorFn: typing.Coroutine):
        """
        Processes jobs from the jobs queue using the provided processor function.

        Args:
            processorFn (typing.Coroutine): The coroutine function used to process jobs from the queue.
        """
        while self.is_alive:
            if not self.queue.empty():
                job = await self.queue.get()
                try:
                    # Process the job using the provided coroutine function
                    await processorFn(job)
                finally:
                    self.queue.task_done()
            else:
                # Sleep briefly if no jobs to process
                await asyncio.sleep(1)

    async def run(self, collectorFn: typing.Coroutine, processorFn: typing.Coroutine):
        """
        Runs both the collector and processor tasks.
        """
        await asyncio.gather(
            self.collector(collectorFn),
            self.processor(processorFn),
        )
