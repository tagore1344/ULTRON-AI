# transparent_overlay.py
import sys

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSlot
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
    from PyQt6.QtGui import QFont, QColor
except Exception:
    Qt = None
    QTimer = None
    pyqtSlot = lambda *args, **kwargs: (lambda f: f)
    QApplication = None
    QMainWindow = object
    QLabel = object
    QVBoxLayout = object
    QWidget = object
    QGraphicsDropShadowEffect = object
    QFont = object
    QColor = object

class UltronTopOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Window Flags: Stay on Top, No Taskbar Icon, Frameless Border
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        
        # 2. Make the background completely transparent & click-through
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # 3. Position the overlay at the top-center of a standard screen
        self.setGeometry(760, 10, 400, 60)
        
        # 4. Core UI layout
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status Label Configuration
        self.status_label = QLabel("ULTRON: SYSTEM IDLE", self)
        self.status_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        
        # Neon Accent Styling matching color #00d4ff
        self.status_label.setStyleSheet("""
            QLabel {
                color: #00d4ff;
                background-color: rgba(10, 15, 25, 120);
                border: 1px solid #00d4ff;
                border-radius: 12px;
                padding: 8px 20px;
                letter-spacing: 2px;
            }
        """)
        
        # Add a subtle sci-fi glow effect
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(15)
        glow.setColor(QColor(0, 212, 255, 180))
        glow.setOffset(0, 0)
        self.status_label.setGraphicsEffect(glow)
        
        self.layout.addWidget(self.status_label)
        self.setCentralWidget(self.central_widget)
        
        print("[OVERLAY] Transparent status layer anchored to screen top.")

    @pyqtSlot(str, str)
    def update_status(self, text, state):
        """
        Explicitly marked as a pyqtSlot to receive cross-thread strings
        from assistant_with_brain.py safely without any errors.
        """
        self.status_label.setText(f"ULTRON: {text.upper()}")
        
        if state == "listening":
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #ff0055;
                    background-color: rgba(25, 5, 10, 160);
                    border: 1px solid #ff0055;
                    border-radius: 12px;
                    padding: 8px 20px;
                    letter-spacing: 2px;
                }
            """)
        elif state == "thinking":
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #00ffaa;
                    background-color: rgba(5, 25, 15, 160);
                    border: 1px solid #00ffaa;
                    border-radius: 12px;
                    padding: 8px 20px;
                    letter-spacing: 2px;
                }
            """)
        else: # Idle / Default
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #00d4ff;
                    background-color: rgba(10, 15, 25, 120);
                    border: 1px solid #00d4ff;
                    border-radius: 12px;
                    padding: 8px 20px;
                    letter-spacing: 2px;
                }
            """)