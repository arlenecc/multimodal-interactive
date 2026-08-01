"""Configuration panel widget - occupies top 1/6 of the window."""
import asyncio
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QObject
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QMessageBox,
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fetch_thread = None
        self._fetch_worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(2)

        label_style = "font-weight: bold; font-size: 11px;"

        # --- Row 1: Base URL, API Key, Model, Fetch button ---
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        url_label = QLabel("Base URL:")
        url_label.setStyleSheet(label_style)
        row1.addWidget(url_label)
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://api.openai.com/v1")
        self.base_url_input.setMinimumWidth(200)
        row1.addWidget(self.base_url_input, 3)

        key_label = QLabel("API Key:")
        key_label.setStyleSheet(label_style)
        row1.addWidget(key_label)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setMinimumWidth(150)
        row1.addWidget(self.api_key_input, 2)

        model_label = QLabel("Model:")
        model_label.setStyleSheet(label_style)
        row1.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(150)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        row1.addWidget(self.model_combo, 2)
        self.fetch_btn = QPushButton("获取模型")
        self.fetch_btn.setFixedWidth(80)
        self.fetch_btn.clicked.connect(self._on_fetch_models)
        row1.addWidget(self.fetch_btn)

        row1.addStretch()
        layout.addLayout(row1)

        # --- Row 2: Max Tokens, Temp, Stream, Send button ---
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        param_label = QLabel("参数:")
        param_label.setStyleSheet(label_style)
        row2.addWidget(param_label)

        row2.addWidget(QLabel("Max Tokens:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 128000)
        self.max_tokens_spin.setValue(4096)
        self.max_tokens_spin.setFixedWidth(80)
        row2.addWidget(self.max_tokens_spin)

        row2.addWidget(QLabel("Temp:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setDecimals(1)
        self.temp_spin.setFixedWidth(60)
        row2.addWidget(self.temp_spin)

        self.stream_check = QCheckBox("Stream")
        self.stream_check.setChecked(True)
        row2.addWidget(self.stream_check)

        row2.addStretch()

        layout.addLayout(row2)

    def _on_fetch_models(self):
        """Fetch models from the API."""
        base_url = self.base_url_input.text().strip()
        api_key = self.api_key_input.text().strip()

        if not base_url:
            QMessageBox.warning(self, "错误", "请先填写 Base URL")
            return

        # Refuse to start a second fetch while one is already running.
        if self._fetch_thread is not None and self._fetch_thread.isRunning():
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
        # Cleanup: delete worker and thread once finished so they don't leak
        # on every fetch.
        self._fetch_thread.finished.connect(self._fetch_worker.deleteLater)
        self._fetch_thread.finished.connect(self._fetch_thread.deleteLater)
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
        elif current:
            # User had a custom model name not in the fetched list; preserve it
            self.model_combo.setCurrentText(current)
        elif models:
            # No previous selection; auto-select first model
            self.model_combo.setCurrentText(models[0])

    def _on_models_error(self, error_msg: str):
        """Handle model fetch error."""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("获取模型")
        QMessageBox.critical(self, "获取模型失败", f"错误: {error_msg}")

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

    def wait_for_fetch(self, timeout_ms: int = 3000):
        """Wait for any in-progress model fetch to finish. Called on app close."""
        if self._fetch_thread is not None and self._fetch_thread.isRunning():
            self._fetch_thread.quit()
            self._fetch_thread.wait(timeout_ms)
