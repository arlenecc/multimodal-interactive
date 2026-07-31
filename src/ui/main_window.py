"""Main window - integrates all panels into the application layout."""
import asyncio
import os
import sys
import time

from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMessageBox, QApplication,
)

from src.config import AppConfig
from src.api_client import MultimodalAPIClient
from src.models.message import Message, MessageRole, Conversation
from src.ui.config_panel import ConfigPanel
from src.ui.chat_panel import ChatPanel
from src.ui.log_panel import LogPanel


CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".multimodal_debugger_config.json")


class APIWorker(QObject):
    """Worker for running API calls in a background thread."""
    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(Message)
    error_occurred = pyqtSignal(str)
    log_entry = pyqtSignal(str, str)  # direction, content

    def __init__(self, config: AppConfig, messages: list, stream: bool = True):
        super().__init__()
        self.config = config
        self.messages = messages
        self.stream = stream

    def run(self):
        try:
            client = MultimodalAPIClient(self.config)
            # Forward log entries to the main thread via signal
            client.set_log_callback(lambda d, c: self.log_entry.emit(d, c))
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if self.stream:
                    full_text = loop.run_until_complete(
                        self._run_stream(client)
                    )
                    msg = Message(role=MessageRole.ASSISTANT, text=full_text)
                else:
                    msg = loop.run_until_complete(client.send_message(self.messages))
                self.response_complete.emit(msg)
            finally:
                loop.close()
        except Exception as e:
            self.error_occurred.emit(str(e))

    async def _run_stream(self, client) -> str:
        """Run streaming request, emit tokens and return full text."""
        full_text = ""
        async for token in client.send_message_stream(self.messages):
            full_text += token
            self.token_received.emit(token)
        return full_text


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("多模态模型调试工具 - Multimodal Model Debugger")
        self.setMinimumSize(1200, 800)
        self._api_thread = None
        self._api_worker = None
        self._api_client = None
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Top: Config panel (1/6 of height)
        self.config_panel = ConfigPanel()
        main_layout.addWidget(self.config_panel, 1)

        # Bottom: Splitter with chat (2/3) and log (1/3)
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.chat_panel = ChatPanel()
        bottom_splitter.addWidget(self.chat_panel)

        self.log_panel = LogPanel()
        bottom_splitter.addWidget(self.log_panel)

        # Set initial sizes: chat=2/3, log=1/3
        total_width = self.minimumWidth()
        bottom_splitter.setSizes([int(total_width * 2 / 3), int(total_width * 1 / 3)])

        main_layout.addWidget(bottom_splitter, 5)

        # Connect signals
        self.chat_panel.message_sent.connect(self._on_message_sent)
        self.config_panel.send_request.connect(self._on_send_request)

        # Initialize API client with log callback
        self._api_client = MultimodalAPIClient(self.config_panel.get_config())
        self._api_client.set_log_callback(self._on_api_log)

    def _load_config(self):
        """Load saved configuration."""
        config = AppConfig.load(CONFIG_FILE)
        self.config_panel.set_config(config)

    def _save_config(self):
        """Save current configuration."""
        config = self.config_panel.get_config()
        config.save(CONFIG_FILE)

    def _on_api_log(self, direction: str, content: str):
        """Handle API log entries from the client."""
        if direction == "request":
            self.log_panel.log_api_request(content)
        elif direction == "response":
            self.log_panel.log_api_response(content)
        else:
            self.log_panel.append_log(direction, content)

    def _on_send_request(self, config: AppConfig):
        """Handle send request from config panel."""
        self._send_message(config)

    def _on_message_sent(self, message: Message):
        """Handle a message sent from the chat panel."""
        config = self.config_panel.get_config()
        self._send_message(config)

    def _send_message(self, config: AppConfig):
        """Send a message to the API."""
        # Validate config
        is_valid, errors = config.validate()
        if not is_valid:
            QMessageBox.warning(self, "配置错误", "\n".join(errors))
            return

        # Update API client config
        self._api_client.update_config(config)

        # Get conversation messages
        messages = self.chat_panel.conversation.messages

        if not messages:
            return

        self.log_panel.log_info(f"发送消息 - 模型: {config.model_name}, 消息数: {len(messages)}")

        # Prepare streaming
        stream = config.stream_enabled
        if stream:
            self.chat_panel.add_streaming_message()

        # Disable send button during request
        self.config_panel.send_btn.setEnabled(False)
        self.config_panel.send_btn.setText("处理中...")
        self.chat_panel.send_btn.setEnabled(False)

        # Start worker thread
        self._api_thread = QThread()
        self._api_worker = APIWorker(config, messages, stream=stream)
        self._api_worker.moveToThread(self._api_thread)

        self._api_thread.started.connect(self._api_worker.run)
        self._api_worker.token_received.connect(self._on_token_received)
        self._api_worker.response_complete.connect(self._on_response_complete)
        self._api_worker.error_occurred.connect(self._on_api_error)
        self._api_worker.log_entry.connect(self._on_api_log)

        # Cleanup
        self._api_worker.response_complete.connect(self._api_thread.quit)
        self._api_worker.error_occurred.connect(self._api_thread.quit)
        self._api_thread.finished.connect(self._enable_send_buttons)

        self._api_thread.start()

    def _on_token_received(self, token: str):
        """Handle a streaming token."""
        self.chat_panel.append_stream_token(token)

    def _on_response_complete(self, message: Message):
        """Handle API response completion."""
        if not self.config_panel.get_config().stream_enabled:
            self.chat_panel.add_message(message)
        else:
            self.chat_panel.finish_streaming_message()

        self.log_panel.log_info(f"响应完成 - 内容长度: {len(message.text)} 字符")
        self._save_config()

    def _on_api_error(self, error_msg: str):
        """Handle API error."""
        self.log_panel.log_error(f"API 错误: {error_msg}")
        if self.config_panel.get_config().stream_enabled:
            self.chat_panel.finish_streaming_message()
        QMessageBox.critical(self, "API 错误", f"请求失败:\n{error_msg}")

    def _enable_send_buttons(self):
        """Re-enable send buttons after request completes."""
        self.config_panel.send_btn.setEnabled(True)
        self.config_panel.send_btn.setText("发送")
        self.chat_panel.send_btn.setEnabled(True)

    def closeEvent(self, event):
        """Save config on close."""
        self._save_config()
        if self._api_thread and self._api_thread.isRunning():
            self._api_thread.quit()
            self._api_thread.wait(3000)
        event.accept()
