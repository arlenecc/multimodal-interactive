"""Tests for API client module."""
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api_client import MultimodalAPIClient
from src.config import AppConfig
from src.models.message import MediaContent, Message, MessageRole, MediaType


class TestMultimodalAPIClient:
    """Test MultimodalAPIClient class."""

    def _make_client(self, **kwargs):
        defaults = {
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-test-key",
            "model_name": "gpt-4o",
        }
        defaults.update(kwargs)
        config = AppConfig(**defaults)
        return MultimodalAPIClient(config)

    def test_init(self):
        """Test client initialization."""
        client = self._make_client()
        assert client.config.model_name == "gpt-4o"
        assert client.config.base_url == "https://api.example.com/v1"

    @pytest.mark.asyncio
    async def test_fetch_models_success(self):
        """Test fetching model list successfully."""
        client = self._make_client()
        mock_response = {
            "data": [
                {"id": "gpt-4o"},
                {"id": "gpt-4o-mini"},
                {"id": "gpt-3.5-turbo"},
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            models = await client.fetch_models()
            assert len(models) == 3
            assert "gpt-4o" in models
            assert "gpt-4o-mini" in models

    @pytest.mark.asyncio
    async def test_fetch_models_empty(self):
        """Test fetching models when response is empty."""
        client = self._make_client()
        with patch.object(client, "_make_request", new_callable=AsyncMock, return_value={"data": []}):
            models = await client.fetch_models()
            assert len(models) == 0

    @pytest.mark.asyncio
    async def test_fetch_models_error(self):
        """Test fetching models with API error."""
        client = self._make_client()
        with patch.object(client, "_make_request", new_callable=AsyncMock, side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await client.fetch_models()

    @pytest.mark.asyncio
    async def test_send_message_text_only(self):
        """Test sending a text-only message."""
        client = self._make_client()
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help?",
                    }
                }
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            msg = Message(role=MessageRole.USER, text="Hi")
            response = await client.send_message([msg])
            assert response.text == "Hello! How can I help?"
            assert response.role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_send_message_multimodal(self):
        """Test sending a multimodal message."""
        client = self._make_client()
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I see a cat in the image.",
                    }
                }
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            media = MediaContent(
                type=MediaType.IMAGE,
                data=base64.b64encode(b"fake").decode(),
                mime_type="image/png",
            )
            msg = Message(role=MessageRole.USER, text="What's in this image?", media=[media])
            response = await client.send_message([msg])
            assert "cat" in response.text

    @pytest.mark.asyncio
    async def test_stream_response(self):
        """Test streaming response."""
        client = self._make_client()
        chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " "}}]},
            {"choices": [{"delta": {"content": "world"}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ]

        async def mock_stream(*args, **kwargs):
            for chunk in chunks:
                yield chunk

        with patch.object(client, "_make_stream_request", new=mock_stream):
            collected = []
            async for kind, token in client.send_message_stream([]):
                collected.append((kind, token))
            assert collected == [
                ("content", "Hello"),
                ("content", " "),
                ("content", "world"),
            ]

    @pytest.mark.asyncio
    async def test_stream_with_reasoning(self):
        """Test streaming response with reasoning content (e.g. DeepSeek)."""
        client = self._make_client()
        chunks = [
            {"choices": [{"delta": {"reasoning_content": "Let me think..."}}]},
            {"choices": [{"delta": {"reasoning_content": " about this"}}]},
            {"choices": [{"delta": {"content": "Answer"}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ]

        async def mock_stream(*args, **kwargs):
            for chunk in chunks:
                yield chunk

        with patch.object(client, "_make_stream_request", new=mock_stream):
            collected = []
            async for kind, token in client.send_message_stream([]):
                collected.append((kind, token))
            assert collected == [
                ("reasoning", "Let me think..."),
                ("reasoning", " about this"),
                ("content", "Answer"),
            ]

    def test_build_headers(self):
        """Test building request headers."""
        client = self._make_client()
        headers = client._build_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer sk-test-key"
        assert "Content-Type" in headers

    def test_build_url(self):
        """Test building API URL."""
        client = self._make_client()
        url = client._build_url("/models")
        assert url == "https://api.example.com/v1/models"

    def test_build_url_no_double_slash(self):
        """Test URL building doesn't create double slashes."""
        client = self._make_client(base_url="https://api.example.com/v1/")
        url = client._build_url("/models")
        assert "//models" not in url.replace("https://", "")

    @pytest.mark.asyncio
    async def test_send_message_with_system_prompt(self):
        """Test sending messages with system prompt."""
        client = self._make_client()
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "OK",
                    }
                }
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            messages = [
                Message(role=MessageRole.SYSTEM, text="You are helpful."),
                Message(role=MessageRole.USER, text="Hi"),
            ]
            await client.send_message(messages)
            call_args = mock_req.call_args
            # _make_request is called with: endpoint, json_data=payload, method="POST"
            body = call_args.kwargs.get("json_data", {})
            assert len(body["messages"]) == 2

    def test_update_config(self):
        """Test updating client configuration."""
        client = self._make_client()
        new_config = AppConfig(
            base_url="https://new-api.example.com/v1",
            api_key="sk-new-key",
            model_name="gpt-4o-mini",
        )
        client.update_config(new_config)
        assert client.config.model_name == "gpt-4o-mini"
        assert client.config.api_key == "sk-new-key"

    @pytest.mark.asyncio
    async def test_fetch_models_sorted(self):
        """Test that fetched models are sorted alphabetically."""
        client = self._make_client()
        mock_response = {
            "data": [
                {"id": "gpt-4o"},
                {"id": "gpt-3.5-turbo"},
                {"id": "gpt-4o-mini"},
            ]
        }
        with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            models = await client.fetch_models()
            assert models == sorted(models)
