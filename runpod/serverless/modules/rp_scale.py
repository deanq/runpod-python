'''
runpod | serverless | rp_scale.py
Provides the functionality for scaling the runpod serverless worker.
'''

from typing import Coroutine
from runpod.serverless.modules.rp_logger import RunPodLogger
from .rp_job import get_job
from .worker_state import JobsQueue


log = RunPodLogger()


class JobScaler():
    """
    Job Scaler. This class is responsible for scaling the number of concurrent requests.
    """

    def __init__(self):
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

    async def collector(self, collectorFn: Coroutine, queue: JobsQueue = JobsQueue()):
        """
        Retrieve jobs from the server

        Returns:
            List[Any]: A list of job data retrieved from the server.
        """
        while self.is_alive():
            log.debug(f"Jobs in progress: {queue.get_job_count()}")
            if job := await collectorFn():
                log.debug(f"Job received {job}")
                await queue.add_job(job)

    async def processor(self, processorFn: Coroutine,queue: JobsQueue = JobsQueue()):
        while self.is_alive():
            job = await queue.get_job()
            await processorFn(job)
            log.debug(f"Job processed {job}")
            queue.task_done()
