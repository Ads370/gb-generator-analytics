"""
This is the HTTP client for the Elexon Insights (BMRS) API.
The API is public, requiring no key. The responses are JSON dicts with the 
records under a 'data' key. This client centralises the base URL, a reused 
session, retry-with-backoff on transient failures, a per-request timeout
and request logging so every ingestion script share the same behaviour.
"""

from __future__ import annotations

import logging
import time
import requests

logger = logging.getLogger(__name__)

class ElexonClient:
    BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

    #HTTPS statuses worht retrying: rate limiting/server-side errors.
    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(
        self, 
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 5,
        backoff_factor: float = 1.5,
    ) -> None:
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        #reused session pools connections across many calls in a run
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def get(self, endpoint: str, params: dict | None = None) -> list[dict]:
        """
        GET an endpoint and return its list of records. Retries transient failures
        with exponential backoff. Raises on a non-retryable HTTP error or after exhausting
        retries, so a broken run fails loudly rather than writing empty data.
        """

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(1, self.max_retries + 1):
            start = time.monotonic()
            try:
                response = self.session.get(
                    url, params=params, timeout=self.timeout
                )
                elapsed = time.monotonic() - start

                if response.status_code in self.RETRY_STATUSES:
                    logger.warning(
                        "%s -> %s (%.2fs), retryable [attemtp %d/%d]",
                        url,
                        response.status_code,
                        elapsed,
                        attempt,
                        self.max_retries,
                    )
                    self._sleep(attempt)
                    continue

                response.raise_for_status()
                logger.info(
                    "%s -> %s (%.2fs)",
                    url,
                    response.status_code,
                    elapsed)
                return self._extract(response.json())
            
            except requests.exceptions.RequestException as exc:
                elapsed = time.monotonic() - start
                logger.warning(
                    "%s -> %s (%.2fs): %s [attemtp %d/%d]",
                    url,
                    elapsed,
                    exc,
                    attempt,
                    self.max_retries,
                )
                if attempt == self.max_retries:
                    raise
                self._sleep(attempt)

        raise RuntimeError(f"Exhausted {self.max_retries} retries for {url}")

    def _sleep(self, attempt: int) -> None:
        """Exponential backoff between attempts."""
        delay = self.backoff_factor ** attempt
        time.sleep(delay)

    @staticmethod
    def _extract(payload: object) -> list[dict]:
        """ Pull the record list out of an Elexon response. Most
        datasets endpointss return {"data":[...]}. Some reference
        endpoints return a bare list. Handle both so the callers always get a list.
        """
        if isinstance(payload, dict):
            data = payload.get("data")
            if data is None:
                #Dict with no data is unexpected. Its better to surface it than
                #silently returning nothing.
                raise ValueError(f"Response dict had no 'data' key; keys were {list(payload)}")
            return data
        if isinstance(payload, list):
            return payload
        raise TypeError(f"Unexpected response type: {type(payload)}")


if __name__ == "__main__":
    # Smoke test: run `python -m ingestion.client` to confirm connectivity.
    logging.basicConfig(level=logging.INFO)
    client = ElexonClient()
    units = client.get("/reference/bmunits/all")
    print(f"Fetched {len(units)} BM units")
        