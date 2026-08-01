"""Message data models for multimodal conversations."""
import base64
import mimetypes
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MessageRole(str, Enum):
    """Message role enum."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MediaType(str, Enum):
    """Media type enum."""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class MediaContent:
    """Represents a piece of media content (text, image, audio, video)."""

    text: Optional[str] = None
    type: Optional[MediaType] = None
    data: Optional[str] = None  # base64 encoded
    mime_type: Optional[str] = None
    file_path: Optional[str] = None

    @classmethod
    def from_file(cls, filepath: str, media_type: MediaType) -> "MediaContent":
        """Create MediaContent from a file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            # Fallback based on media_type
            mime_map = {
                MediaType.IMAGE: "image/png",
                MediaType.AUDIO: "audio/mpeg",
                MediaType.VIDEO: "video/mp4",
            }
            mime_type = mime_map.get(media_type, "application/octet-stream")

        with open(filepath, "rb") as f:
            file_data = f.read()

        b64_data = base64.b64encode(file_data).decode("utf-8")

        return cls(
            type=media_type,
            data=b64_data,
            mime_type=mime_type,
            file_path=filepath,
        )

    def to_openai_format(self) -> dict:
        """Convert to OpenAI API content format."""
        if self.text is not None and self.type is None:
            return {"type": "text", "text": self.text}

        if self.type == MediaType.IMAGE:
            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{self.mime_type};base64,{self.data}",
                },
            }
        elif self.type == MediaType.AUDIO:
            return {
                "type": "input_audio",
                "input_audio": {
                    "data": self.data,
                    "format": self._get_audio_format(),
                },
            }
        elif self.type == MediaType.VIDEO:
            # Video is typically passed as a URL or frame extraction
            return {
                "type": "video_url",
                "video_url": {
                    "url": f"data:{self.mime_type};base64,{self.data}",
                },
            }
        return {"type": "text", "text": ""}

    def _get_audio_format(self) -> str:
        """Get audio format string for OpenAI API."""
        if self.mime_type:
            fmt_map = {
                "audio/wav": "wav",
                "audio/x-wav": "wav",
                "audio/mp3": "mp3",
                "audio/mpeg": "mp3",
                "audio/ogg": "ogg",
                "audio/flac": "flac",
                "audio/aac": "aac",
                # m4a container typically holds AAC audio; mime detection
                # varies by platform (mp4 / x-m4a / mp4a-latm).
                "audio/mp4": "aac",
                "audio/x-m4a": "aac",
                "audio/m4a": "aac",
                "audio/mp4a-latm": "aac",
            }
            return fmt_map.get(self.mime_type, "wav")
        return "wav"


@dataclass
class Message:
    """Represents a chat message with optional media content."""

    role: MessageRole
    text: str = ""
    media: List[MediaContent] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reasoning: str = ""

    def to_openai_format(self) -> dict:
        """Convert to OpenAI API message format."""
        if not self.media:
            return {
                "role": self.role.value,
                "content": self.text,
            }

        content_parts = []
        if self.text:
            content_parts.append({"type": "text", "text": self.text})
        for m in self.media:
            content_parts.append(m.to_openai_format())

        return {
            "role": self.role.value,
            "content": content_parts,
        }


@dataclass
class Conversation:
    """Manages a conversation with multiple messages."""

    messages: List[Message] = field(default_factory=list)

    def add_message(self, message: Message):
        """Add a message to the conversation."""
        self.messages.append(message)

    def clear(self):
        """Clear all messages."""
        self.messages.clear()

    @property
    def last_message(self) -> Optional[Message]:
        """Get the last message in the conversation."""
        if not self.messages:
            return None
        return self.messages[-1]

    def get_messages_by_role(self, role: MessageRole) -> List[Message]:
        """Get all messages with a specific role."""
        return [m for m in self.messages if m.role == role]

    def to_openai_messages(self) -> List[dict]:
        """Convert all messages to OpenAI API format."""
        return [m.to_openai_format() for m in self.messages]
