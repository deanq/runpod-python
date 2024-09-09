"""
This module defines the Heartbeat class.
The heartbeat is responsible for sending periodic pings to the Runpod server.
"""
import os
import time
import threading

import requests
from requests.adapters import HTTPAdapter, Retry

from runpod.http_client import SyncClientSession
from runpod.version import __version__ as runpod_version
from runpod.serverless.modules.rp_logger import RunPodLogger
from runpod.serverless.modules.worker_state import JobsQueue, WORKER_ID


log = RunPodLogger()
jobs = JobsQueue()  # Contains the list of jobs that are currently running.


class Heartbeat:
    ''' Sends heartbeats to the Runpod server. '''

    PING_URL = os.environ.get('RUNPOD_WEBHOOK_PING', "PING_NOT_SET")
    PING_URL = PING_URL.replace('$RUNPOD_POD_ID', WORKER_ID)
    PING_INTERVAL = int(os.environ.get('RUNPOD_PING_INTERVAL', 10000))//1000

    _thread_started = False

    def __init__(self, pool_connections=10, retries=3) -> None:
        '''
        Initializes the Heartbeat class.
        '''
        self._session = SyncClientSession()
        self._session.headers.update({"Authorization": os.environ.get('RUNPOD_AI_API_KEY')})

        retry_strategy = Retry(
            total=retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1
        )

        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_connections,
            max_retries=retry_strategy
        )
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

        self._stop_event = threading.Event()  # Event to signal the heartbeat to stop
        self._thread = None  # Thread for the ping loop

    def start_ping(self, test=False):
        '''
        Sends heartbeat pings to the Runpod server.
        '''
        if os.environ.get('RUNPOD_AI_API_KEY') is None:
            log.debug("Not deployed on RunPod serverless, pings will not be sent.")
            return

        if os.environ.get('RUNPOD_POD_ID') is None:
            log.info("Not running on RunPod, pings will not be sent.")
            return

        if self.PING_URL in ["PING_NOT_SET", None]:
            log.error("Ping URL not set, cannot start ping.")
            return

        log.info(f"Starting heartbeats with interval {self.PING_INTERVAL} seconds.")
        self._thread = threading.Thread(target=self.ping_loop, args=(test,), daemon=True)
        self._thread.start()

    def ping_loop(self, test=False):
        '''
        Continuously sends heartbeat pings to the Runpod server in the background.
        '''
        while not self._stop_event.is_set():
            self._send_ping()
            time.sleep(self.ping_interval)  # Sleep for the ping interval

            if test:
                return

    def _send_ping(self):
        '''
        Sends a heartbeat to the Runpod server.
        '''
        job_ids = jobs.get_job_list()
        ping_params = {
            'job_id': job_ids,
            'runpod_version': runpod_version
        }

        try:
            result = self._session.get(
                self.PING_URL, params=ping_params,
                timeout=self.PING_INTERVAL*2
            )
            if result.status_code == 200:
                log.debug(f"Heartbeat Sent | URL: {self.PING_URL} | Status: {result.status_code}")
            else:
                log.error(f"Failed to send heartbeat, status code: {result.status_code}")

        except requests.RequestException as err:
            log.error(f"Ping Request Error: {err}, attempting to restart ping.")

    def stop_ping(self):
        '''
        Stops the heartbeat pings by setting the stop event and waiting for the thread to finish.
        '''
        log.info("Stopping heartbeat pings.")
        self._stop_event.set()
        if self._thread:
            self._thread.join()  # Wait for the ping thread to finish
        self._session.close()  # Close the session
