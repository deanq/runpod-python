"""
RunPod | API Wrapper | GraphQL
"""

import json
import os
from typing import Any, Dict

from runpod import error
from runpod.http_client import SyncClientSession
from runpod.user_agent import USER_AGENT

HTTP_STATUS_UNAUTHORIZED = 401


def run_graphql_query(query: str) -> Dict[str, Any]:
    '''
    Run a GraphQL query
    '''
    from runpod import api_key  # pylint: disable=import-outside-toplevel, cyclic-import
    api_url_base = os.getenv("RUNPOD_API_BASE_URL", "https://api.runpod.io")
    api_key = api_key or os.getenv("RUNPOD_AI_API_KEY")
    url = f"{api_url_base}/graphql?api_key={api_key}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }

    data = json.dumps({"query": query})
    response = SyncClientSession().post(url, headers=headers, data=data, timeout=30)

    if response.status_code == HTTP_STATUS_UNAUTHORIZED:
        raise error.AuthenticationError("Unauthorized request, please check your API key.")

    if "errors" in response.json():
        raise error.QueryError(
            response.json()["errors"][0]["message"],
            query
        )

    return response.json()
