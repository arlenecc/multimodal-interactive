"""Tests for media utility functions."""
import base64
import os
import tempfile

import pytest

from src.utils.media_utils import (
    detect_media_type,
    encode_file_to_base64,
    get_file_size_str,
    is_supported_image_format,
    is_supported_audio_format,
    is_supported_video_format,
    is_supported_format,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
)


class TestDetectMediaType:
    """Test media type detection."""

    def test_detect_png(self):
        assert detect_media_type("photo.png") == "image"

    def test_detect_jpg(self):
        assert detect_media_type("photo.jpg") == "image"

    def test_detect_jpeg(self):
        assert detect_media_type("photo.jpeg") == "image"

    def test_detect_gif(self):
        assert detect_media_type("photo.gif") == "image"

    def test_detect_webp(self):
        assert detect_media_type("photo.webp") == "image"

    def test_detect_mp3(self):
        assert detect_media_type("audio.mp3") == "audio"

    def test_detect_wav(self):
        assert detect_media_type("audio.wav") == "audio"

    def test_detect_ogg(self):
        assert detect_media_type("audio.ogg") == "audio"

    def test_detect_mp4(self):
        assert detect_media_type("video.mp4") == "video"

    def test_detect_mov(self):
        assert detect_media_type("video.mov") == "video"

    def test_detect_webm(self):
        assert detect_media_type("video.webm") == "video"
    def test_detect_unknown(self):
        result = detect_media_type("file.xyz")
        assert result is None

    def test_detect_case_insensitive(self):
        assert detect_media_type("Photo.PNG") == "image"
        assert detect_media_type("Audio.MP3") == "audio"

    def test_detect_with_path(self):
        assert detect_media_type("/path/to/image.png") == "image"
        assert detect_media_type("C:\\Users\\test\\video.mp4") == "video"


class TestEncodeFileToBase64:
    """Test base64 encoding of files."""

    def test_encode_small_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Hello, World!")
        result = encode_file_to_base64(str(test_file))
        decoded = base64.b64decode(result)
        assert decoded == b"Hello, World!"

    def test_encode_binary_file(self, tmp_path):
        test_file = tmp_path / "test.bin"
        binary_data = bytes(range(256))
        test_file.write_bytes(binary_data)
        result = encode_file_to_base64(str(test_file))
        decoded = base64.b64decode(result)
        assert decoded == binary_data

    def test_encode_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            encode_file_to_base64("/nonexistent/file.txt")

    def test_encode_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")
        result = encode_file_to_base64(str(test_file))
        assert result == ""


class TestGetFileSizeStr:
    """Test file size formatting."""

    def test_bytes(self):
        assert get_file_size_str(500) == "500 B"

    def test_kilobytes(self):
        result = get_file_size_str(1024)
        assert "KB" in result

    def test_megabytes(self):
        result = get_file_size_str(1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = get_file_size_str(1024 * 1024 * 1024)
        assert "GB" in result

    def test_zero(self):
        assert get_file_size_str(0) == "0 B"


class TestSupportedFormats:
    """Test format support checking."""

    def test_image_formats(self):
        assert is_supported_image_format("png") is True
        assert is_supported_image_format("jpg") is True
        assert is_supported_image_format("jpeg") is True
        assert is_supported_image_format("gif") is True
        assert is_supported_image_format("webp") is True
        assert is_supported_image_format("bmp") is True
        assert is_supported_image_format("tiff") is False

    def test_audio_formats(self):
        assert is_supported_audio_format("mp3") is True
        assert is_supported_audio_format("wav") is True
        assert is_supported_audio_format("ogg") is True
        assert is_supported_audio_format("flac") is True
        assert is_supported_audio_format("aac") is False

    def test_video_formats(self):
        assert is_supported_video_format("mp4") is True
        assert is_supported_video_format("webm") is True
        assert is_supported_video_format("mov") is True
        assert is_supported_video_format("avi") is True
        assert is_supported_video_format("flv") is False

    def test_is_supported_format(self):
        assert is_supported_format("png") is True
        assert is_supported_format("mp3") is True
        assert is_supported_format("mp4") is True
        assert is_supported_format("xyz") is False

    def test_case_insensitive_check(self):
        assert is_supported_format("PNG") is True
        assert is_supported_format("MP3") is True
        assert is_supported_format("MP4") is True
