# transparent_overlay.py
import sys
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PyQt6.QtGui import QFont, QColor

class UltronTopOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setGeometry(760, 10, 400, 60)

        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("TAG: SYSTEM IDLE", self)
        self.status_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self._set_style("idle")

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(15)
        glow.setColor(QColor(0, 212, 255, 180))
        glow.setOffset(0, 0)
        self.status_label.setGraphicsEffect(glow)

        self.layout.addWidget(self.status_label)
        self.setCentralWidget(self.central_widget)
        print("[OVERLAY] TAG transparent status layer anchored to screen top.")

    def _set_style(self, state):
        styles = {
            "listening": ("#ff0055", "rgba(25, 5, 10, 160)"),
            "thinking": ("#00ffaa", "rgba(5, 25, 15, 160)"),
            "idle": ("#00d4ff", "rgba(10, 15, 25, 120)"),
        }
        color, background = styles.get(state, styles["idle"])
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: {background};
                border: 1px solid {color};
                border-radius: 12px;
                padding: 8px 20px;
                letter-spacing: 2px;
            }}
        """)

    @pyqtSlot(str, str)
    def update_status(self, text, state):
        self.status_label.setText(f"TAG: {text.upper()}")
        self._set_style(state)
