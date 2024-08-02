'''
runpod | serverless | rp_scale.py
Provides the functionality for scaling the runpod serverless worker.
'''

import asyncio
import typing

from runpod.serverless.modules.rp_logger import RunPodLogger
from .rp_job import get_job
from .worker_state import Jobs

log = RunPodLogger()
job_list = Jobs()


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

    async def get_jobs(self, session):
        """
        Retrieve multiple jobs from the server.

        Yields:
            AsyncGenerator[Dict[str, Any], None]: A generator of jobs retrieved from the server.
        """
        while self.is_alive():
            tasks = [
                asyncio.create_task(get_job(session, retry=False))
                for _ in range(job_list.get_job_count())
            ]
            log.debug(f"Get jobs: {tasks}")

            async for response in asyncio.as_completed(tasks):
                log.debug(f"Got job: {response}")
                yield response.result()

        asyncio.get_event_loop().stop()
