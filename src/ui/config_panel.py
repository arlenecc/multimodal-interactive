"""Configuration panel widget - occupies top 1/6 of the window."""
import asyncio
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QObject
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QGroupBox, QMessageBox, QFileDialog,
)

from src.config import AppConfig


class FetchModelsWorker(QObject):
    """Worker for fetching models in background thread."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config

    def run(self):
        try:
            from src.api_client import MultimodalAPIClient
            client = MultimodalAPIClient(self.config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                models = loop.run_until_complete(client.fetch_models())
                self.finished.emit(models)
            finally:
                loop.close()
        except Exception as e:
            self.error.emit(str(e))


class ConfigPanel(QWidget):
    """Configuration panel with API settings."""

    config_changed = pyqtSignal(AppConfig)
    send_request = pyqtSignal(AppConfig)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fetch_thread = None
        self._fetch_worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Base URL
        url_group = QVBoxLayout()
        url_group.setSpacing(2)
        url_label = QLabel("Base URL:")
        url_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://api.openai.com/v1")
        self.base_url_input.setMinimumWidth(200)
        url_group.addWidget(url_label)
        url_group.addWidget(self.base_url_input)
        layout.addLayout(url_group, 3)

        # API Key
        key_group = QVBoxLayout()
        key_group.setSpacing(2)
        key_label = QLabel("API Key:")
        key_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setMinimumWidth(150)
        key_group.addWidget(key_label)
        key_group.addWidget(self.api_key_input)
        layout.addLayout(key_group, 2)

        # Model
        model_group = QVBoxLayout()
        model_group.setSpacing(2)
        model_label = QLabel("Model:")
        model_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        model_row = QHBoxLayout()
        model_row.setSpacing(4)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(150)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.fetch_btn = QPushButton("获取模型")
        self.fetch_btn.setFixedWidth(80)
        self.fetch_btn.clicked.connect(self._on_fetch_models)
        model_row.addWidget(self.model_combo)
        model_row.addWidget(self.fetch_btn)
        model_group.addWidget(model_label)
        model_group.addLayout(model_row)
        layout.addLayout(model_group, 2)

        # Parameters
        param_group = QVBoxLayout()
        param_group.setSpacing(2)
        param_label = QLabel("参数:")
        param_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        param_row = QHBoxLayout()
        param_row.setSpacing(4)

        # Max tokens
        param_row.addWidget(QLabel("Max Tokens:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 128000)
        self.max_tokens_spin.setValue(4096)
        self.max_tokens_spin.setFixedWidth(80)
        param_row.addWidget(self.max_tokens_spin)

        # Temperature
        param_row.addWidget(QLabel("Temp:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setDecimals(1)
        self.temp_spin.setFixedWidth(60)
        param_row.addWidget(self.temp_spin)

        # Stream
        self.stream_check = QCheckBox("Stream")
        self.stream_check.setChecked(True)
        param_row.addWidget(self.stream_check)

        param_group.addWidget(param_label)
        param_group.addLayout(param_row)
        layout.addLayout(param_group, 2)

        # Send button
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedWidth(80)
        self.send_btn.setMinimumHeight(40)
        self.send_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.send_btn.clicked.connect(self._on_send)
        layout.addWidget(self.send_btn)

    def _on_fetch_models(self):
        """Fetch models from the API."""
        base_url = self.base_url_input.text().strip()
        api_key = self.api_key_input.text().strip()

        if not base_url:
            QMessageBox.warning(self, "错误", "请先填写 Base URL")
            return

        config = AppConfig(base_url=base_url, api_key=api_key, model_name="")
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("获取中...")

        self._fetch_thread = QThread()
        self._fetch_worker = FetchModelsWorker(config)
        self._fetch_worker.moveToThread(self._fetch_thread)
        self._fetch_thread.started.connect(self._fetch_worker.run)
        self._fetch_worker.finished.connect(self._on_models_fetched)
        self._fetch_worker.error.connect(self._on_models_error)
        self._fetch_worker.finished.connect(self._fetch_thread.quit)
        self._fetch_worker.error.connect(self._fetch_thread.quit)
        self._fetch_thread.start()

    def _on_models_fetched(self, models: list):
        """Handle successful model fetch."""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("获取模型")
        current = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        # Restore previous selection if still available
        idx = self.model_combo.findText(current)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        elif models:
            self.model_combo.setCurrentText(models[0])

    def _on_models_error(self, error_msg: str):
        """Handle model fetch error."""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("获取模型")
        QMessageBox.critical(self, "获取模型失败", f"错误: {error_msg}")

    def _on_send(self):
        """Handle send button click."""
        config = self.get_config()
        self.send_request.emit(config)

    def get_config(self) -> AppConfig:
        """Get current configuration from UI."""
        return AppConfig(
            base_url=self.base_url_input.text().strip(),
            api_key=self.api_key_input.text().strip(),
            model_name=self.model_combo.currentText().strip(),
            max_tokens=self.max_tokens_spin.value(),
            temperature=self.temp_spin.value(),
            stream_enabled=self.stream_check.isChecked(),
        )

    def set_config(self, config: AppConfig):
        """Set configuration to UI."""
        self.base_url_input.setText(config.base_url)
        self.api_key_input.setText(config.api_key)
        if config.model_name:
            self.model_combo.setCurrentText(config.model_name)
        self.max_tokens_spin.setValue(config.max_tokens)
        self.temp_spin.setValue(config.temperature)
        self.stream_check.setChecked(config.stream_enabled)
