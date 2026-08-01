"""Log panel widget - displays API interaction logs for debugging."""
import html
from datetime import datetime

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLabel, QPushButton, QHBoxLayout,
)


class LogPanel(QWidget):
    """Log panel showing detailed API communication for debugging."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        title = QLabel("交互日志")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.clear_btn = QPushButton("清除")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self.clear)
        header_layout.addWidget(self.clear_btn)

        self.auto_scroll_check = QPushButton("自动滚动")
        self.auto_scroll_check.setFixedWidth(70)
        self.auto_scroll_check.setCheckable(True)
        self.auto_scroll_check.setChecked(True)
        header_layout.addWidget(self.auto_scroll_check)

        layout.addLayout(header_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Menlo, Monaco, Courier New, monospace")
        # Cap retained blocks so a long debugging session doesn't blow up
        # memory (each append() adds one block; oldest are evicted automatically).
        # setMaximumBlockCount is on QTextDocument, not QTextEdit.
        self.log_text.document().setMaximumBlockCount(1000)
        self.log_text.setStyleSheet(
            "QTextEdit { background-color: #ffffff; color: #333333; "
            "font-size: 11px; border: 1px solid #ddd; }"
        )
        layout.addWidget(self.log_text)

    def append_log(self, direction: str, content: str):
        """Append a log entry.

        Args:
            direction: 'request' or 'response'
            content: The log content
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if direction == "request":
            color = "#1565C0"  # Blue
            icon = ">>>"
        elif direction == "response":
            color = "#2E7D32"  # Green
            icon = "<<<"
        elif direction == "error":
            color = "#C62828"  # Red
            icon = "!!!"
        elif direction == "info":
            color = "#F57F17"  # Amber
            icon = "---"
        else:
            color = "#333333"
            icon = "..."

        # Escape content so HTML/<script>/etc. in API responses is shown literally
        # instead of being interpreted by the QTextEdit's HTML renderer.
        safe_content = html.escape(content, quote=False)

        html_out = (
            f'<div style="margin: 2px 0;">'
            f'<span style="color: #999999;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: bold;">{icon} {direction.upper()}</span>'
            f'<pre style="color: {color}; margin: 2px 0 2px 16px; white-space: pre-wrap;">'
            f'{safe_content}</pre>'
            f'</div>'
        )
        self.log_text.append(html_out)

        if self.auto_scroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """Clear all log entries."""
        self.log_text.clear()

    def log_api_request(self, content: str):
        """Log an API request."""
        self.append_log("request", content)

    def log_api_response(self, content: str):
        """Log an API response."""
        self.append_log("response", content)

    def log_error(self, content: str):
        """Log an error."""
        self.append_log("error", content)

    def log_info(self, content: str):
        """Log an info message."""
        self.append_log("info", content)
