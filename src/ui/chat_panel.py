"""Chat panel widget - displays multimodal conversation and input."""
import os
import time

from PyQt6.QtCore import pyqtSignal, Qt, QSize, QEvent, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QScrollArea, QFrame, QFileDialog, QSizePolicy,
    QProgressBar, QToolButton, QMenu, QMessageBox, QApplication,
)

from src.models.message import Message, MessageRole, MediaContent, MediaType, Conversation
from src.utils.media_utils import (
    detect_media_type, get_file_size_str, get_file_filter_string,
    SUPPORTED_IMAGE_EXTENSIONS,
)


class MediaPreviewWidget(QFrame):
    """Widget to preview attached media files."""

    media_removed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_items = []
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(4)
        self.setStyleSheet("QFrame { background-color: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; }")
        self.layout.addStretch()

    def add_media(self, filepath: str, media_type: str):
        """Add a media preview."""
        item_frame = QFrame()
        item_frame.setStyleSheet("QFrame { background-color: white; border: 1px solid #ccc; border-radius: 4px; padding: 4px; }")
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(4, 4, 4, 4)
        item_layout.setSpacing(2)

        filename = os.path.basename(filepath)
        file_size = get_file_size_str(os.path.getsize(filepath))

        if media_type == "image":
            # Show image thumbnail
            label = QLabel()
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(scaled)
            else:
                label.setText("[图片]")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item_layout.addWidget(label)
        else:
            # Show icon for audio/video
            icon_map = {"audio": "🎵", "video": "🎬"}
            icon_label = QLabel(icon_map.get(media_type, "📎"))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("font-size: 32px;")
            item_layout.addWidget(icon_label)

        info_label = QLabel(f"{filename}\n{file_size}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 10px; color: #666;")
        info_label.setWordWrap(True)
        info_label.setMaximumWidth(100)
        item_layout.addWidget(info_label)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("QPushButton { color: red; border: none; font-weight: bold; }")
        idx = len(self._media_items)
        remove_btn.clicked.connect(lambda: self._remove_media(idx, item_frame))
        item_layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._media_items.append({"path": filepath, "type": media_type, "widget": item_frame})

        # Insert before the stretch
        self.layout.insertWidget(self.layout.count() - 1, item_frame)
        self.show()

    def _remove_media(self, idx: int, widget: QFrame):
        """Remove a media item."""
        # Find and remove the widget
        for i, item in enumerate(self._media_items):
            if item["widget"] is widget:
                self._media_items.pop(i)
                widget.setParent(None)
                widget.deleteLater()
                self.media_removed.emit(i)
                break

        if not self._media_items:
            self.hide()

    def get_media_items(self) -> list:
        """Get list of attached media items."""
        return [{"path": item["path"], "type": item["type"]} for item in self._media_items]

    def clear_all(self):
        """Remove all media previews."""
        for item in self._media_items:
            item["widget"].setParent(None)
            item["widget"].deleteLater()
        self._media_items.clear()
        self.hide()


class MessageBubble(QFrame):
    """A single message bubble in the chat."""

    def __init__(self, message: Message, parent=None):
        super().__init__(parent)
        self.message = message
        self._setup_ui()

    def _setup_ui(self):
        is_user = self.message.role == MessageRole.USER
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 2, 8, 2)

        # Role label
        role_text = "用户" if is_user else "助手"
        role_color = "#2196F3" if is_user else "#4CAF50"
        role_label = QLabel(role_text)
        role_label.setStyleSheet(f"color: {role_color}; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(role_label)

        # Content bubble
        bubble = QFrame()
        bg_color = "#E3F2FD" if is_user else "#F1F8E9"
        bubble.setStyleSheet(
            f"QFrame {{ background-color: {bg_color}; border-radius: 8px; padding: 8px; }}"
        )
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(8, 8, 8, 8)
        bubble_layout.setSpacing(4)

        # Text content
        if self.message.text:
            text_label = QLabel(self.message.text)
            text_label.setWordWrap(True)
            # Use PlainText so HTML/code/markdown from the model is shown literally
            # rather than being rendered (which would break display of <tags> etc.)
            text_label.setTextFormat(Qt.TextFormat.PlainText)
            text_label.setStyleSheet("font-size: 13px; background: transparent;")
            text_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
            )
            # Rich text would interpret <...>; PlainText shows raw text safely.
            bubble_layout.addWidget(text_label)

        # Media content
        for media in self.message.media:
            if media.type == MediaType.IMAGE and media.file_path:
                img_label = QLabel()
                pixmap = QPixmap(media.file_path)
                if not pixmap.isNull():
                    max_width = 300
                    max_height = 400
                    if pixmap.width() > max_width or pixmap.height() > max_height:
                        pixmap = pixmap.scaled(
                            max_width, max_height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    img_label.setPixmap(pixmap)
                else:
                    img_label.setText(f"[图片: {media.file_path}]")
                img_label.setStyleSheet("background: transparent;")
                bubble_layout.addWidget(img_label)
            elif media.type == MediaType.AUDIO:
                audio_label = QLabel(f"🎵 音频文件: {os.path.basename(media.file_path or 'audio')}" if media.file_path else "🎵 音频内容")
                audio_label.setStyleSheet("background: transparent; color: #1565C0;")
                bubble_layout.addWidget(audio_label)
            elif media.type == MediaType.VIDEO:
                video_label = QLabel(f"🎬 视频文件: {os.path.basename(media.file_path or 'video')}" if media.file_path else "🎬 视频内容")
                video_label.setStyleSheet("background: transparent; color: #1565C0;")
                bubble_layout.addWidget(video_label)

        main_layout.addWidget(bubble)

        # Timestamp
        time_str = self.message.timestamp.strftime("%H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #999; font-size: 10px;")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(time_label)


class ChatPanel(QWidget):
    """Chat panel with multimodal message display and input."""

    message_sent = pyqtSignal(Message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation = Conversation()
        self._streaming_label = None
        self._stream_start_time = None
        self._stream_token_count = 0
        self._stream_text = ""
        self._stream_role_label = None
        self._last_ui_update_ts = 0.0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Chat messages area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #ddd; }")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(0)
        self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area, 1)

        # Speed indicator
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #999; font-size: 11px;")
        self.speed_label.hide()
        layout.addWidget(self.speed_label)

        # Media preview area
        self.media_preview = MediaPreviewWidget()
        layout.addWidget(self.media_preview)

        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)

        # Attach button
        self.attach_btn = QToolButton()
        self.attach_btn.setText("📎")
        self.attach_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.attach_btn.setFixedWidth(40)
        self.attach_btn.setFixedHeight(36)
        self.attach_btn.setStyleSheet("QToolButton { font-size: 18px; }")

        attach_menu = QMenu(self)
        attach_menu.addAction("📷 图片", lambda: self._attach_file("image"))
        attach_menu.addAction("🎵 音频", lambda: self._attach_file("audio"))
        attach_menu.addAction("🎬 视频", lambda: self._attach_file("video"))
        attach_menu.addAction("📁 文件", lambda: self._attach_file("any"))
        self.attach_btn.setMenu(attach_menu)
        input_layout.addWidget(self.attach_btn)

        # Text input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("输入消息... (Enter 发送, Shift+Enter 换行)")
        self.text_input.setMaximumHeight(80)
        self.text_input.setMinimumHeight(36)
        self.text_input.setStyleSheet(
            "QTextEdit { border: 1px solid #ccc; border-radius: 4px; padding: 6px; font-size: 13px; }"
        )
        # QTextEdit consumes Return; install an event filter so we can intercept
        # Enter (without Shift) to send, while Shift+Enter still inserts a newline.
        self.text_input.installEventFilter(self)
        input_layout.addWidget(self.text_input, 1)

        # Send button
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedWidth(60)
        self.send_btn.setFixedHeight(36)
        self.send_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1976D2; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self.send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # Clear button
        bottom_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清空对话")
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.setStyleSheet("QPushButton { color: #999; }")
        self.clear_btn.clicked.connect(self.clear_chat)
        bottom_layout.addWidget(self.clear_btn)
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)

    def _attach_file(self, file_type: str):
        """Open file dialog to attach a file."""
        if file_type == "image":
            filter_str = "图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"
        elif file_type == "audio":
            filter_str = "音频文件 (*.mp3 *.wav *.ogg *.flac *.m4a)"
        elif file_type == "video":
            filter_str = "视频文件 (*.mp4 *.mov *.avi *.mkv *.webm)"
        else:
            filter_str = get_file_filter_string()

        filepath, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filter_str)
        if not filepath:
            return

        media_type = detect_media_type(filepath)
        if media_type is None:
            QMessageBox.warning(
                self, "不支持的文件",
                f"不支持的文件类型：{os.path.basename(filepath)}\n"
                "仅支持图片、音频、视频文件。",
            )
            return

        self.media_preview.add_media(filepath, media_type)

    def _on_send(self):
        """Handle send button click."""
        text = self.text_input.toPlainText().strip()
        media_items = self.media_preview.get_media_items()

        # Allow sending text only, media only, or both
        if not text and not media_items:
            return

        # Build message
        media_contents = []
        for item in media_items:
            mt_map = {"image": MediaType.IMAGE, "audio": MediaType.AUDIO, "video": MediaType.VIDEO}
            mt = mt_map.get(item["type"], MediaType.IMAGE)
            try:
                mc = MediaContent.from_file(item["path"], mt)
                media_contents.append(mc)
            except Exception:
                continue

        msg = Message(role=MessageRole.USER, text=text, media=media_contents)
        self.add_message(msg)
        self.message_sent.emit(msg)

        # Clear input
        self.text_input.clear()
        self.media_preview.clear_all()
        # Keep focus on the input so the user can immediately type the next
        # message (clicking the send button moves focus away otherwise).
        self.text_input.setFocus()

    def add_message(self, message: Message):
        """Add a message to the chat display."""
        self.conversation.add_message(message)
        bubble = MessageBubble(message)
        # Insert before the stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def add_streaming_message(self):
        """Prepare for a streaming response message."""
        self._streaming_label = QLabel("")
        self._streaming_label.setWordWrap(True)
        # PlainText so model output containing <tags> is shown literally
        self._streaming_label.setTextFormat(Qt.TextFormat.PlainText)
        self._streaming_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._streaming_label.setStyleSheet(
            "QLabel { background-color: #F1F8E9; border-radius: 8px; padding: 8px; font-size: 13px; }"
        )

        # Role label (kept reference so we can remove it when finalizing)
        self._stream_role_label = QLabel("助手")
        self._stream_role_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 11px;")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._stream_role_label)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._streaming_label)

        self._stream_start_time = time.time()
        self._stream_token_count = 0
        self._stream_text = ""
        self._last_ui_update_ts = 0.0
        self.speed_label.show()
        self._scroll_to_bottom()

    def append_stream_token(self, token: str):
        """Append a streaming token to the current response."""
        if self._streaming_label is None:
            return

        self._stream_text += token
        self._stream_token_count += 1

        # Throttle label updates: re-rendering the whole label on every token is
        # O(n^2) for long responses. Update the visible text at most ~30 times/s.
        # The final text is always shown because finish_streaming_message()
        # replaces the streaming label with a real bubble built from _stream_text.
        now = time.time()
        if now - self._last_ui_update_ts >= 0.033:
            self._streaming_label.setText(self._stream_text)
            self._last_ui_update_ts = now
            self._scroll_to_bottom()

        # Update speed indicator (cheap; can run every token)
        elapsed = now - self._stream_start_time
        if elapsed > 0:
            tokens_per_sec = self._stream_token_count / elapsed
            self.speed_label.setText(
                f"推理速度: {tokens_per_sec:.1f} tokens/s | "
                f"已用时间: {elapsed:.1f}s | Tokens: {self._stream_token_count}"
            )

    def finish_streaming_message(self):
        """Finalize the streaming message and replace the streaming label with
        a proper MessageBubble so it has a consistent look (timestamp, etc.)."""
        if self._streaming_label is None:
            return

        final_text = self._stream_text
        msg = Message(role=MessageRole.ASSISTANT, text=final_text)
        self.conversation.add_message(msg)

        # Remove the temporary streaming widgets from the layout and replace
        # them with a real bubble built from the finalized message.
        streaming_label = self._streaming_label
        role_label = self._stream_role_label

        role_label.setParent(None)
        role_label.deleteLater()
        streaming_label.setParent(None)
        streaming_label.deleteLater()

        bubble = MessageBubble(msg)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        self._streaming_label = None
        self._stream_role_label = None
        self._stream_start_time = None
        self._stream_token_count = 0
        self._stream_text = ""
        self.speed_label.hide()
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll the chat area to the bottom.

        Deferred to the next event-loop iteration because at the call site
        the layout hasn't necessarily recomputed yet, so scrollbar.maximum()
        may still reflect the old content height.
        """
        QTimer.singleShot(0, self._do_scroll_to_bottom)

    def _do_scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_chat(self):
        """Clear all chat messages."""
        self.conversation.clear()
        # Remove all widgets except the stretch
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._streaming_label = None
        self._stream_role_label = None
        self._stream_start_time = None
        self._stream_token_count = 0
        self._stream_text = ""
        self.speed_label.hide()

    def eventFilter(self, obj, event):
        """Intercept Return/Enter on the text input to send the message.

        QTextEdit consumes the Return key, so ChatPanel.keyPressEvent never
        receives it. The event filter lets us intercept before QTextEdit
        handles it: Enter sends, Shift+Enter inserts a newline.

        We also avoid intercepting Enter while the input method is composing
        (e.g. Chinese pinyin), because Enter is used to commit the preedit
        text in that case — sending the message would be wrong.
        """
        if obj is self.text_input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    # Shift+Enter: let QTextEdit insert a newline.
                    return False
                # Don't hijack Enter while the IME is composing (Chinese/Japanese
                # input methods use Enter to commit the candidate).
                im = QApplication.inputMethod()
                if im is not None and im.isComposing():
                    return False
                self._on_send()
                return True  # swallow so QTextEdit doesn't insert a newline
        return super().eventFilter(obj, event)
