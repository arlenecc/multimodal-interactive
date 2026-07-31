"""Entry point for the Multimodal Model Debugger application."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """Launch the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Multimodal Model Debugger")
    app.setApplicationDisplayName("多模态模型调试工具")

    # Set application style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
