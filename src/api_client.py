"""OpenAI-compatible API client for multimodal models."""
import json
import time
from typing import AsyncGenerator, Callable, List, Optional

import httpx

from src.config import AppConfig
from src.models.message import MediaContent, Message, MessageRole, MediaType


class MultimodalAPIClient:
    """Client for interacting with OpenAI-compatible multimodal APIs."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._log_callback: Optional[Callable] = None

    def set_log_callback(self, callback: Callable):
        """Set a callback function for logging API interactions."""
        self._log_callback = callback

    def _log(self, direction: str, content: str):
        """Log an API interaction."""
        if self._log_callback:
            self._log_callback(direction, content)

    def update_config(self, config: AppConfig):
        """Update the client configuration."""
        self.config = config

    def _build_headers(self) -> dict:
        """Build HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _build_url(self, endpoint: str) -> str:
        """Build full API URL from endpoint."""
        base = self.config.base_url.rstrip("/")
        if endpoint.startswith("/"):
            return f"{base}{endpoint}"
        return f"{base}/{endpoint}"

    async def _make_request(self, endpoint: str, json_data: dict = None, method: str = "GET") -> dict:
        """Make an HTTP request to the API."""
        url = self._build_url(endpoint)
        headers = self._build_headers()

        request_info = f"{method} {url}\n"
        if json_data:
            request_info += f"Body: {json.dumps(json_data, ensure_ascii=False, indent=2)[:2000]}"
        self._log("request", request_info)

        async with httpx.AsyncClient(timeout=120.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            else:
                response = await client.post(url, headers=headers, json=json_data)

            response_text = response.text[:5000]
            self._log("response", f"Status: {response.status_code}\n{response_text}")

            response.raise_for_status()
            return response.json()

    async def _make_stream_request(self, endpoint: str, json_data: dict) -> AsyncGenerator[dict, None]:
        """Make a streaming HTTP request to the API."""
        url = self._build_url(endpoint)
        headers = self._build_headers()

        request_info = f"POST {url} (stream)\nBody: {json.dumps(json_data, ensure_ascii=False, indent=2)[:2000]}"
        self._log("request", request_info)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=json_data) as response:
                self._log("response", f"Status: {response.status_code} (streaming)")
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue

    async def fetch_models(self) -> List[str]:
        """Fetch available model list from the API."""
        response = await self._make_request("/models")
        models = [m["id"] for m in response.get("data", [])]
        return sorted(models)

    async def send_message(self, messages: List[Message]) -> Message:
        """Send messages and get a response (non-streaming)."""
        openai_messages = [m.to_openai_format() for m in messages]
        payload = {
            "model": self.config.model_name,
            "messages": openai_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False,
        }

        response_data = await self._make_request("/chat/completions", json_data=payload, method="POST")

        choice = response_data.get("choices", [{}])[0]
        msg_data = choice.get("message", {})
        content = msg_data.get("content", "")

        # Parse response content for any media
        response_msg = Message(
            role=MessageRole.ASSISTANT,
            text=content if isinstance(content, str) else str(content),
        )
        return response_msg

    async def send_message_stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """Send messages and stream the response token by token."""
        openai_messages = [m.to_openai_format() for m in messages]
        payload = {
            "model": self.config.model_name,
            "messages": openai_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }

        async for chunk in self._make_stream_request("/chat/completions", json_data=payload):
            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                yield content
