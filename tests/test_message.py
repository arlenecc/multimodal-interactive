"""Tests for message data models."""
import base64
import os
import tempfile

import pytest

from src.models.message import (
    MediaContent,
    Message,
    MessageRole,
    Conversation,
    MediaType,
)


class TestMessageRole:
    """Test MessageRole enum."""

    def test_role_values(self):
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"


class TestMediaType:
    """Test MediaType enum."""

    def test_media_type_values(self):
        assert MediaType.IMAGE == "image"
        assert MediaType.AUDIO == "audio"
        assert MediaType.VIDEO == "video"


class TestMediaContent:
    """Test MediaContent class."""

    def test_text_content(self):
        """Test creating text content."""
        media = MediaContent(text="Hello world")
        assert media.type is None
        assert media.text == "Hello world"
        assert media.data is None
        assert media.mime_type is None

    def test_image_from_base64(self):
        """Test creating image content from base64."""
        b64data = base64.b64encode(b"fake image data").decode()
        media = MediaContent(
            type=MediaType.IMAGE,
            data=b64data,
            mime_type="image/png",
        )
        assert media.type == MediaType.IMAGE
        assert media.data == b64data
        assert media.mime_type == "image/png"

    def test_image_from_file(self, tmp_path):
        """Test creating image content from file."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake png data")
        media = MediaContent.from_file(str(img_file), MediaType.IMAGE)
        assert media.type == MediaType.IMAGE
        assert media.mime_type == "image/png"
        assert media.data is not None

    def test_audio_from_file(self, tmp_path):
        """Test creating audio content from file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake mp3 data")
        media = MediaContent.from_file(str(audio_file), MediaType.AUDIO)
        assert media.type == MediaType.AUDIO
        assert media.mime_type == "audio/mpeg"

    def test_video_from_file(self, tmp_path):
        """Test creating video content from file."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake mp4 data")
        media = MediaContent.from_file(str(video_file), MediaType.VIDEO)
        assert media.type == MediaType.VIDEO
        assert media.mime_type == "video/mp4"

    def test_from_file_nonexistent(self):
        """Test from_file with nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            MediaContent.from_file("/nonexistent/file.png", MediaType.IMAGE)

    def test_to_openai_format_text(self):
        """Test converting text to OpenAI format."""
        media = MediaContent(text="Hello")
        fmt = media.to_openai_format()
        assert fmt == {"type": "text", "text": "Hello"}

    def test_to_openai_format_image(self):
        """Test converting image to OpenAI format."""
        b64data = base64.b64encode(b"fake").decode()
        media = MediaContent(
            type=MediaType.IMAGE,
            data=b64data,
            mime_type="image/png",
        )
        fmt = media.to_openai_format()
        assert fmt["type"] == "image_url"
        assert "url" in fmt["image_url"]
        assert fmt["image_url"]["url"].startswith("data:image/png;base64,")

    def test_to_openai_format_audio(self):
        """Test converting audio to OpenAI format."""
        b64data = base64.b64encode(b"fake").decode()
        media = MediaContent(
            type=MediaType.AUDIO,
            data=b64data,
            mime_type="audio/wav",
        )
        fmt = media.to_openai_format()
        assert fmt["type"] == "input_audio"
        assert "data" in fmt["input_audio"]

    def test_audio_format_m4a(self):
        """Test that m4a audio is mapped to aac, not incorrectly to wav."""
        b64data = base64.b64encode(b"fake").decode()
        # m4a mime type varies by platform
        for m4a_mime in ("audio/mp4", "audio/x-m4a", "audio/m4a", "audio/mp4a-latm"):
            media = MediaContent(
                type=MediaType.AUDIO,
                data=b64data,
                mime_type=m4a_mime,
            )
            assert media._get_audio_format() == "aac", f"Failed for {m4a_mime}"

    def test_audio_format_wav(self):
        """Test wav audio format mapping."""
        media = MediaContent(
            type=MediaType.AUDIO,
            data="fake",
            mime_type="audio/wav",
        )
        assert media._get_audio_format() == "wav"

    def test_audio_format_mp3(self):
        """Test mp3 audio format mapping."""
        media = MediaContent(
            type=MediaType.AUDIO,
            data="fake",
            mime_type="audio/mpeg",
        )
        assert media._get_audio_format() == "mp3"

    def test_to_openai_format_video(self):
        """Test converting video to OpenAI format."""
        b64data = base64.b64encode(b"fake").decode()
        media = MediaContent(
            type=MediaType.VIDEO,
            data=b64data,
            mime_type="video/mp4",
        )
        fmt = media.to_openai_format()
        assert fmt["type"] == "video_url" or "video" in str(fmt).lower()


class TestMessage:
    """Test Message class."""

    def test_text_only_message(self):
        """Test creating a text-only message."""
        msg = Message(role=MessageRole.USER, text="Hello")
        assert msg.role == MessageRole.USER
        assert msg.text == "Hello"
        assert len(msg.media) == 0
        assert msg.timestamp is not None

    def test_multimodal_message(self):
        """Test creating a multimodal message."""
        media = MediaContent(
            type=MediaType.IMAGE,
            data=base64.b64encode(b"fake").decode(),
            mime_type="image/png",
        )
        msg = Message(
            role=MessageRole.USER,
            text="What is in this image?",
            media=[media],
        )
        assert msg.text == "What is in this image?"
        assert len(msg.media) == 1
        assert msg.media[0].type == MediaType.IMAGE

    def test_to_openai_format_text_only(self):
        """Test converting text-only message to OpenAI format."""
        msg = Message(role=MessageRole.USER, text="Hello")
        fmt = msg.to_openai_format()
        assert fmt["role"] == "user"
        assert fmt["content"] == "Hello"

    def test_to_openai_format_multimodal(self):
        """Test converting multimodal message to OpenAI format."""
        media = MediaContent(
            type=MediaType.IMAGE,
            data=base64.b64encode(b"fake").decode(),
            mime_type="image/png",
        )
        msg = Message(
            role=MessageRole.USER,
            text="Describe this",
            media=[media],
        )
        fmt = msg.to_openai_format()
        assert fmt["role"] == "user"
        assert isinstance(fmt["content"], list)
        types = [item["type"] for item in fmt["content"]]
        assert "text" in types
        assert "image_url" in types

    def test_media_only_message(self):
        """Test creating a message with only media, no text."""
        media = MediaContent(
            type=MediaType.IMAGE,
            data=base64.b64encode(b"fake").decode(),
            mime_type="image/png",
        )
        msg = Message(role=MessageRole.USER, media=[media])
        assert msg.text == ""
        assert len(msg.media) == 1

    def test_message_with_id(self):
        """Test message has unique ID."""
        msg1 = Message(role=MessageRole.USER, text="First")
        msg2 = Message(role=MessageRole.USER, text="Second")
        assert msg1.id != msg2.id


class TestConversation:
    """Test Conversation class."""

    def test_empty_conversation(self):
        """Test creating an empty conversation."""
        conv = Conversation()
        assert len(conv.messages) == 0

    def test_add_message(self):
        """Test adding messages to conversation."""
        conv = Conversation()
        msg = Message(role=MessageRole.USER, text="Hello")
        conv.add_message(msg)
        assert len(conv.messages) == 1
        assert conv.messages[0].text == "Hello"

    def test_add_multiple_messages(self):
        """Test adding multiple messages."""
        conv = Conversation()
        conv.add_message(Message(role=MessageRole.USER, text="Hi"))
        conv.add_message(Message(role=MessageRole.ASSISTANT, text="Hello!"))
        conv.add_message(Message(role=MessageRole.USER, text="How are you?"))
        assert len(conv.messages) == 3

    def test_to_openai_messages(self):
        """Test converting conversation to OpenAI format."""
        conv = Conversation()
        conv.add_message(Message(role=MessageRole.SYSTEM, text="You are helpful."))
        conv.add_message(Message(role=MessageRole.USER, text="Hello"))
        messages = conv.to_openai_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_clear_conversation(self):
        """Test clearing conversation."""
        conv = Conversation()
        conv.add_message(Message(role=MessageRole.USER, text="Hello"))
        conv.clear()
        assert len(conv.messages) == 0

    def test_last_message(self):
        """Test getting the last message."""
        conv = Conversation()
        conv.add_message(Message(role=MessageRole.USER, text="First"))
        conv.add_message(Message(role=MessageRole.ASSISTANT, text="Second"))
        assert conv.last_message.text == "Second"

    def test_last_message_empty(self):
        """Test getting last message from empty conversation."""
        conv = Conversation()
        assert conv.last_message is None

    def test_get_messages_by_role(self):
        """Test filtering messages by role."""
        conv = Conversation()
        conv.add_message(Message(role=MessageRole.USER, text="Q1"))
        conv.add_message(Message(role=MessageRole.ASSISTANT, text="A1"))
        conv.add_message(Message(role=MessageRole.USER, text="Q2"))
        user_msgs = conv.get_messages_by_role(MessageRole.USER)
        assert len(user_msgs) == 2
        assert all(m.role == MessageRole.USER for m in user_msgs)
