"""Application entry point with dark theme support."""
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QIcon
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def get_icon_path() -> Path | None:
    """Get path to app icon, checking multiple locations."""
    # PyInstaller stores bundled files in sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "app.ico"
        if bundled.exists():
            return bundled

    candidates = [
        Path(__file__).parent.parent / "app.ico",  # Development: project root
        Path(sys.executable).parent / "app.ico",   # PyInstaller: next to exe
        Path(__file__).parent / "app.ico",         # Fallback: gui folder
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def apply_dark_theme(app: QApplication) -> None:
    """Apply a dark color palette to the application."""
    app.setStyle("Fusion")

    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))

    app.setPalette(palette)


def launch_app() -> int:
    """Launch the application and return exit code."""
    app = QApplication(sys.argv)
    app.setApplicationName("Hand History De-anonymizer")
    app.setApplicationDisplayName("Hand History De-anonymizer")
    app.setDesktopFileName("Hand History De-anonymizer")

    icon_path = get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))

    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_app())
