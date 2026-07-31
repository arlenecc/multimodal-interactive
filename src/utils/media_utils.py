"""Media utility functions for file handling and format detection."""
import base64
import mimetypes
import os

# Supported format extensions
SUPPORTED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
SUPPORTED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "flac", "m4a"}
SUPPORTED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}


def detect_media_type(filepath: str) -> str | None:
    """Detect the media type from file extension.

    Returns 'image', 'audio', 'video', or None if unknown.
    """
    ext = os.path.splitext(filepath)[1].lower().lstrip(".")

    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    elif ext in SUPPORTED_AUDIO_EXTENSIONS:
        return "audio"
    elif ext in SUPPORTED_VIDEO_EXTENSIONS:
        return "video"
    return None


def encode_file_to_base64(filepath: str) -> str:
    """Encode a file to base64 string."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "rb") as f:
        data = f.read()

    return base64.b64encode(data).decode("utf-8")


def get_file_size_str(size_bytes: int) -> str:
    """Format file size as human-readable string."""
    if size_bytes == 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def is_supported_image_format(ext: str) -> bool:
    """Check if an image format is supported."""
    return ext.lower().lstrip(".") in SUPPORTED_IMAGE_EXTENSIONS


def is_supported_audio_format(ext: str) -> bool:
    """Check if an audio format is supported."""
    return ext.lower().lstrip(".") in SUPPORTED_AUDIO_EXTENSIONS


def is_supported_video_format(ext: str) -> bool:
    """Check if a video format is supported."""
    return ext.lower().lstrip(".") in SUPPORTED_VIDEO_EXTENSIONS


def is_supported_format(ext: str) -> bool:
    """Check if any media format is supported."""
    ext_lower = ext.lower().lstrip(".")
    return (
        ext_lower in SUPPORTED_IMAGE_EXTENSIONS
        or ext_lower in SUPPORTED_AUDIO_EXTENSIONS
        or ext_lower in SUPPORTED_VIDEO_EXTENSIONS
    )


def get_mime_type(filepath: str) -> str:
    """Get MIME type from file path."""
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type or "application/octet-stream"


def get_file_filter_string() -> str:
    """Get file filter string for file dialogs."""
    all_supported = []
    for ext in SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS:
        all_supported.append(f"*.{ext}")

    image_str = " ".join(f"*.{ext}" for ext in sorted(SUPPORTED_IMAGE_EXTENSIONS))
    audio_str = " ".join(f"*.{ext}" for ext in sorted(SUPPORTED_AUDIO_EXTENSIONS))
    video_str = " ".join(f"*.{ext}" for ext in sorted(SUPPORTED_VIDEO_EXTENSIONS))
    all_str = " ".join(sorted(all_supported))

    return (
        f"所有支持的文件 ({all_str});;"
        f"图片文件 ({image_str});;"
        f"音频文件 ({audio_str});;"
        f"视频文件 ({video_str});;"
        f"所有文件 (*)"
    )
