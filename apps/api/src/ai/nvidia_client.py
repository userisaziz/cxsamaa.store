"""LLM client with provider dispatch — supports NVIDIA NIM and DeepSeek.

Both providers are OpenAI-compatible, so chat_completion routes to whichever
is configured via the LLM_PROVIDER env var:
  - "deepseek" (default): DeepSeek V4 (Flash or Pro) — fast, cheap
  - "nvidia":              NVIDIA NIM (Llama 3.3 70B, etc.)

The singleton `nvidia_client` is retained for backward compatibility with all
existing callers (scorer, analyzer, role_classifier).
"""
import logging
import time
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class NVIDIAAPIError(Exception):
    """Base exception for LLM API errors (covers both NVIDIA and DeepSeek)."""

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


def _get_llm_provider_config() -> dict[str, str | int]:
    """Return (base_url, api_key, default_model, timeout, provider_name) for the active LLM provider."""
    provider = settings.llm_provider.lower()
    if provider == "deepseek":
        return {
            "base_url": settings.deepseek_base_url.rstrip("/"),
            "api_key": settings.deepseek_api_key,
            "default_model": settings.deepseek_llm_model,
            "timeout": settings.deepseek_timeout,
            "provider_name": "DeepSeek",
        }
    else:
        return {
            "base_url": settings.nvidia_base_url.rstrip("/"),
            "api_key": settings.nvidia_api_key,
            "default_model": settings.nvidia_llm_model,
            "timeout": settings.nvidia_timeout,
            "provider_name": "NVIDIA",
        }


class NVIDIAClient:
    """HTTP client for LLM APIs (NVIDIA NIM + DeepSeek) with retry logic.

    The name is retained for backward compatibility — this client transparently
    routes chat completions to whichever LLM provider is configured.
    """

    def __init__(self):
        # NVIDIA-specific settings (still used for embeddings, multipart uploads)
        self.nvidia_base_url = settings.nvidia_base_url
        self.nvidia_api_key = settings.nvidia_api_key
        self.timeout = settings.nvidia_timeout
        self._max_retries = 3
        self._retry_base_delay = 2  # seconds

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Accept": "application/json",
        }

    def _should_retry(self, status_code: int) -> bool:
        """Determine if request should be retried based on status code."""
        return status_code in (429, 500, 502, 503, 504)

    def _handle_error_response(self, response: httpx.Response, provider_name: str = "API") -> None:
        """Handle error responses from the API."""
        if response.status_code == 401 or response.status_code == 403:
            raise NVIDIAAuthError(
                f"{provider_name} authentication failed: {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )
        elif response.status_code == 429:
            raise NVIDIARateLimitError(
                f"{provider_name} rate limit exceeded: {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )
        else:
            raise NVIDIAAPIError(
                f"{provider_name} error ({response.status_code}): {response.text}",
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

        Used for NVIDIA-specific endpoints (embeddings, etc.)

        Args:
            endpoint: API endpoint path (appended to nvidia_base_url)
            json_data: JSON payload
            extra_headers: Additional headers to include

        Returns:
            Parsed JSON response
        """
        url = f"{self.nvidia_base_url}{endpoint}"
        headers = {**self._get_headers(), "Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)

        last_error = None
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(self._max_retries):
                try:
                    logger.debug(f"NIM API POST {endpoint} (attempt {attempt + 1}/{self._max_retries})")
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

                    self._handle_error_response(response, "NVIDIA")

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

        Used for audio file uploads (diarization). NVIDIA-only.

        Args:
            endpoint: API endpoint path
            files: Files dict for httpx
            data: Additional form data
            extra_headers: Additional headers

        Returns:
            Parsed JSON response
        """
        url = f"{self.nvidia_base_url}{endpoint}"
        headers = self._get_headers()
        if extra_headers:
            headers.update(extra_headers)

        last_error = None
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(self._max_retries):
                try:
                    # Seek file streams back to start on retry
                    if attempt > 0:
                        for key, file_tuple in files.items():
                            if hasattr(file_tuple[1], 'seek'):
                                file_tuple[1].seek(0)

                    logger.debug(f"NIM API POST {endpoint} (multipart, attempt {attempt + 1})")
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

                    self._handle_error_response(response, "NVIDIA")

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

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        """Call LLM chat completions — dispatches to DeepSeek or NVIDIA based on LLM_PROVIDER.

        Both providers use OpenAI-compatible /chat/completions endpoints.

        Args:
            messages: List of {role, content} message dicts
            model: Model override (defaults to provider's configured model)
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            response_format: Optional response format (e.g. {"type": "json_object"})

        Returns:
            The assistant's response text content
        """
        cfg = _get_llm_provider_config()
        provider_name = cfg["provider_name"]

        payload: dict[str, Any] = {
            "model": model or cfg["default_model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        url = f"{cfg['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        last_error = None
        with httpx.Client(timeout=cfg["timeout"]) as client:
            for attempt in range(self._max_retries):
                try:
                    logger.debug(
                        f"{provider_name} chat/completions (model={payload['model']}, "
                        f"attempt {attempt + 1}/{self._max_retries})"
                    )
                    response = client.post(url, json=payload, headers=headers)

                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        if not choices:
                            raise NVIDIAAPIError(
                                f"{provider_name}: No choices in chat completion response"
                            )
                        return choices[0].get("message", {}).get("content", "")

                    if self._should_retry(response.status_code) and attempt < self._max_retries - 1:
                        delay = self._retry_base_delay * (2 ** attempt)
                        logger.warning(
                            f"{provider_name} {response.status_code}, "
                            f"retrying in {delay}s (attempt {attempt + 1})"
                        )
                        time.sleep(delay)
                        continue

                    self._handle_error_response(response, provider_name)

                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    last_error = exc
                    if attempt < self._max_retries - 1:
                        delay = self._retry_base_delay * (2 ** attempt)
                        logger.warning(
                            f"{provider_name} connection error: {exc}, "
                            f"retrying in {delay}s (attempt {attempt + 1})"
                        )
                        time.sleep(delay)
                        continue
                    raise NVIDIAAPIError(
                        f"{provider_name} connection failed after {self._max_retries} attempts: {exc}"
                    )

        raise NVIDIAAPIError(f"{provider_name} failed after {self._max_retries} retries: {last_error}")

    def embeddings(
        self,
        input_texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings via NVIDIA NIM /embeddings endpoint.

        Note: Embeddings always go through NVIDIA NIM regardless of LLM_PROVIDER,
        as DeepSeek does not provide an embeddings endpoint used here.

        Args:
            input_texts: List of text strings to embed
            model: Model override (defaults to settings.nvidia_embedding_model)

        Returns:
            List of embedding vectors (list of float lists)
        """
        payload = {
            "model": model or settings.nvidia_embedding_model,
            "input": input_texts,
            "input_type": "query",
            "encoding_format": "float",
        }
        response = self.post_json("/embeddings", payload)
        data = response.get("data", [])
        if not data:
            raise NVIDIAAPIError("No data in embeddings response")
        # Sort by index to preserve order
        data.sort(key=lambda x: x.get("index", 0))
        embeddings = []
        for item in data:
            emb = item.get("embedding")
            if emb is None:
                raise NVIDIAAPIError(f"Missing embedding in embeddings response item: {item}")
            embeddings.append(emb)
        return embeddings


# Singleton client instance — used by scorer, analyzer, role_classifier
nvidia_client = NVIDIAClient()
