"""HTTP client with retry, timeout, and safe logging for external APIs."""

from dataclasses import dataclass
import logging
from typing import Any, Dict, Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.util.retry import Retry


@dataclass
class HttpClientConfig:
    """Configuration for :class:`ExternalApiClient`."""

    timeout: int = 60
    max_retries: int = 3
    backoff_factor: float = 2.0
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)


class ExternalApiClient:
    """Lightweight HTTP client that applies retry and timeout defaults."""

    def __init__(
        self,
        config: Optional[HttpClientConfig] = None,
        *,
        session: Optional[requests.Session] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or HttpClientConfig()
        self.session = session or self._create_session()
        self.logger = logger or logging.getLogger("external_api")

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=self.config.retry_on_status,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        auth: Optional[tuple] = None,
    ) -> Response:
        """Send an HTTP request with retry support and safe logging."""

        request_timeout = timeout or self.config.timeout
        self._log_request(method, url)

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                data=data,
                params=params,
                timeout=request_timeout,
                auth=auth,
            )
        except RequestException as exc:  # pragma: no cover - exercised via tests
            self._log_error(method, url, str(exc))
            raise

        self._log_response(method, url, response.status_code)
        return response

    def _log_request(self, method: str, url: str) -> None:
        self.logger.info("API Request: %s %s", method, url)

    def _log_response(self, method: str, url: str, status: int) -> None:
        self.logger.info("API Response: %s %s -> %s", method, url, status)

    def _log_error(self, method: str, url: str, error: str) -> None:
        self.logger.error("API Error: %s %s -> %s", method, url, error)

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)
