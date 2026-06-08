"""Base NVIDIA NIM API client with retry logic and error handling."""
import logging
import time
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class NVIDIAAPIError(Exception):
    """Base exception for NVIDIA API errors."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class NVIDIARateLimitError(NVIDIAAPIError):
    """Rate limit exceeded."""
    pass


class NVIDIAAuthError(NVIDIAAPIError):
    """Authentication failed."""
    pass


class NVIDIAClient:
    """HTTP client for NVIDIA NIM API with retry logic."""

    def __init__(self):
        self.base_url = settings.nvidia_base_url
        self.api_key = settings.nvidia_api_key
        self.timeout = settings.nvidia_timeout
        self._max_retries = 3
        self._retry_base_delay = 2  # seconds

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _should_retry(self, status_code: int) -> bool:
        """Determine if request should be retried based on status code."""
        return status_code in (429, 500, 502, 503, 504)

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        if response.status_code == 401 or response.status_code == 403:
            raise NVIDIAAuthError(
                f"Authentication failed: {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )
        elif response.status_code == 429:
            raise NVIDIARateLimitError(
                f"Rate limit exceeded: {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )
        else:
            raise NVIDIAAPIError(
                f"API error ({response.status_code}): {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )

    def post_json(
        self,
        endpoint: str,
        json_data: dict[str, Any],
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """POST JSON to NVIDIA NIM API with retry logic.

        Args:
            endpoint: API endpoint path (appended to base_url)
            json_data: JSON payload
            extra_headers: Additional headers to include

        Returns:
            Parsed JSON response

        Raises:
            NVIDIAAPIError: If the API returns an error after retries
        """
        url = f"{self.base_url}{endpoint}"
        headers = {**self._get_headers(), "Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)

        last_error = None
        for attempt in range(self._max_retries):
            try:
                logger.debug(f"NIM API POST {endpoint} (attempt {attempt + 1}/{self._max_retries})")
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=json_data, headers=headers)

                if response.status_code == 200:
                    return response.json()

                if self._should_retry(response.status_code) and attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"NIM API {endpoint} returned {response.status_code}, "
                        f"retrying in {delay}s (attempt {attempt + 1})"
                    )
                    time.sleep(delay)
                    continue

                self._handle_error_response(response)

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"NIM API {endpoint} connection error: {exc}, "
                        f"retrying in {delay}s (attempt {attempt + 1})"
                    )
                    time.sleep(delay)
                    continue
                raise NVIDIAAPIError(f"Connection failed after {self._max_retries} attempts: {exc}")

        raise NVIDIAAPIError(f"Failed after {self._max_retries} retries: {last_error}")

    def post_multipart(
        self,
        endpoint: str,
        files: dict[str, Any],
        data: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """POST multipart form data to NVIDIA NIM API with retry logic.

        Used for audio file uploads (STT, diarization).

        Args:
            endpoint: API endpoint path
            files: Files dict for httpx
            data: Additional form data
            extra_headers: Additional headers

        Returns:
            Parsed JSON response
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        # Don't set Content-Type — httpx sets it automatically for multipart
        if extra_headers:
            headers.update(extra_headers)

        last_error = None
        for attempt in range(self._max_retries):
            try:
                logger.debug(f"NIM API POST {endpoint} (multipart, attempt {attempt + 1})")
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, files=files, data=data or {}, headers=headers)

                if response.status_code == 200:
                    return response.json()

                if self._should_retry(response.status_code) and attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"NIM API {endpoint} returned {response.status_code}, "
                        f"retrying in {delay}s (attempt {attempt + 1})"
                    )
                    time.sleep(delay)
                    continue

                self._handle_error_response(response)

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"NIM API {endpoint} connection error: {exc}, "
                        f"retrying in {delay}s (attempt {attempt + 1})"
                    )
                    time.sleep(delay)
                    continue
                raise NVIDIAAPIError(f"Connection failed after {self._max_retries} attempts: {exc}")

        raise NVIDIAAPIError(f"Failed after {self._max_retries} retries: {last_error}")


# Singleton client instance
nvidia_client = NVIDIAClient()
