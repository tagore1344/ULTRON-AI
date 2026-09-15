# transparent_overlay.py
# TAG desktop HUD aligned with the Figma control-center design.
# Keeps the existing update_status(text, state) interface used by the backend.

import math
import sys

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class OrbWidget(QWidget):
    """Animated TAG state orb used by the HUD."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "idle"
        self._phase = 0.0
        self.setMinimumSize(260, 260)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)

    def set_state(self, state: str):
        self._state = state if state in {"idle", "listening", "thinking", "speaking", "offline"} else "idle"
        self.update()

    def _tick(self):
        self._phase += 0.08
        self.update()

    def _colors(self):
        return {
            "idle": (QColor("#35E6FF"), QColor("#173544")),
            "listening": (QColor("#35E6FF"), QColor("#104E60")),
            "thinking": (QColor("#8A72FF"), QColor("#33245D")),
            "speaking": (QColor("#43E09B"), QColor("#164B3A")),
            "offline": (QColor("#FF5E72"), QColor("#5B202B")),
        }[self._state]

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent, secondary = self._colors()

        cx = self.width() / 2
        cy = self.height() / 2
        pulse = 1.0 + (0.035 * math.sin(self._phase * 1.4)) if self._state != "offline" else 1.0

        for radius, alpha, color in [
            (108 * pulse, 38, secondary),
            (88 * pulse, 70, secondary),
        ]:
            c = QColor(color)
            c.setAlpha(alpha)
            painter.setBrush(c)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        pen = QPen(accent, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(cx - 112), int(cy - 112), 224, 224)
        painter.drawEllipse(int(cx - 86), int(cy - 86), 172, 172)

        core_radius = 34 if self._state != "thinking" else 30 + int(5 * (0.5 + 0.5 * math.sin(self._phase * 2.0)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(int(cx - core_radius), int(cy - core_radius), core_radius * 2, core_radius * 2)


class StatusPill(QFrame):
    def __init__(self, text: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        self.set_color(color)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.addWidget(self.label)

    def set_color(self, color: str):
        self.setStyleSheet(
            f"QFrame#StatusPill {{ background: rgba(13,19,28,180); border: 1px solid {color}; border-radius: 9px; }}"
            f"QLabel {{ color: {color}; }}"
        )


class UltronTopOverlay(QMainWindow):
    """TAG HUD window.

    Kept under the legacy class name so existing ULTRON imports do not break.
    """

    STATE_CONFIG = {
        "idle": ("SYSTEM IDLE", "READY", "#35E6FF"),
        "listening": ("LISTENING", "CAPTURING VOICE", "#35E6FF"),
        "thinking": ("THINKING", "REASONING", "#8A72FF"),
        "speaking": ("SPEAKING", "VOICE OUTPUT", "#43E09B"),
        "offline": ("OFFLINE", "SYSTEM UNAVAILABLE", "#FF5E72"),
    }

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(1180, 760)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + max(0, (geo.width() - self.width()) // 2),
                geo.y() + max(0, (geo.height() - self.height()) // 2),
            )

        self._build_ui()
        self._set_state("idle")
        print("[OVERLAY] TAG desktop HUD initialized with translucent glass surfaces.")

    def _build_ui(self):
        shell = QFrame()
        shell.setObjectName("Shell")
        shell.setStyleSheet(
            "QFrame#Shell { background: rgba(10,13,18,205); border: 1px solid rgba(74,92,118,170); border-radius: 22px; }"
            "QFrame#Panel { background: rgba(17,23,34,182); border: 1px solid rgba(74,92,118,135); border-radius: 16px; }"
            "QFrame#SubPanel { background: rgba(21,28,40,158); border: 1px solid rgba(74,92,118,120); border-radius: 13px; }"
            "QLabel { color: #F4F7FB; }"
            "QLabel[muted=\"true\"] { color: #8E9AAF; }"
        )
        self.setCentralWidget(shell)

        root = QHBoxLayout(shell)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        sidebar = QFrame()
        sidebar.setObjectName("Panel")
        sidebar.setFixedWidth(200)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 18, 18, 18)
        side.setSpacing(8)

        brand = QLabel("TAG")
        brand.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        side.addWidget(brand)
        subtitle = QLabel("AUTONOMOUS AI")
        subtitle.setStyleSheet("color:#35E6FF;")
        subtitle.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        side.addWidget(subtitle)
        side.addSpacing(20)

        self.nav_labels = []
        for name in ("OVERVIEW", "CONVERSATION", "MEMORY", "TASKS", "VOICE", "SETTINGS"):
            item = QLabel(name)
            item.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
            item.setStyleSheet(
                "color:#F4F7FB; background:rgba(24,35,49,150); border:1px solid rgba(53,230,255,130); border-radius:9px; padding:10px 12px;"
                if name == "OVERVIEW"
                else "color:#8E9AAF; padding:10px 12px;"
            )
            side.addWidget(item)
            self.nav_labels.append(item)

        side.addStretch()
        system = QFrame()
        system.setObjectName("SubPanel")
        system_layout = QVBoxLayout(system)
        system_layout.setContentsMargins(12, 12, 12, 12)
        lbl = QLabel("SYSTEM")
        lbl.setProperty("muted", True)
        lbl.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        system_layout.addWidget(lbl)
        self.online_label = QLabel("● ONLINE")
        self.online_label.setStyleSheet("color:#43E09B;")
        self.online_label.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        system_layout.addWidget(self.online_label)
        detail = QLabel("Local model + tools")
        detail.setProperty("muted", True)
        detail.setFont(QFont("Inter", 8))
        system_layout.addWidget(detail)
        side.addWidget(system)
        root.addWidget(sidebar)

        content = QVBoxLayout()
        content.setSpacing(12)
        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Control Center")
        title.setFont(QFont("Inter", 24, QFont.Weight.DemiBold))
        ready = QLabel("TAG is ready")
        ready.setProperty("muted", True)
        ready.setFont(QFont("Inter", 9))
        title_box.addWidget(title)
        title_box.addWidget(ready)
        title_row.addLayout(title_box)
        title_row.addStretch()
        for metric in ("CPU 23%", "RAM 41%", "MODEL LOCAL"):
            metric_label = QLabel(metric)
            metric_label.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
            metric_label.setStyleSheet("color:#8E9AAF; padding-left:12px;")
            title_row.addWidget(metric_label)
        content.addLayout(title_row)

        center_row = QHBoxLayout()
        center_row.setSpacing(12)

        session = QFrame()
        session.setObjectName("Panel")
        session_layout = QVBoxLayout(session)
        session_layout.setContentsMargins(20, 18, 20, 16)

        live = QLabel("LIVE SESSION")
        live.setProperty("muted", True)
        live.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        session_layout.addWidget(live)
        user = QLabel("Tell me what is running right now.")
        user.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        session_layout.addWidget(user)
        meta = QLabel("YOU  •  LIVE")
        meta.setProperty("muted", True)
        meta.setFont(QFont("Inter", 8))
        session_layout.addWidget(meta)

        response = QFrame()
        response.setObjectName("SubPanel")
        response_layout = QVBoxLayout(response)
        response_layout.setContentsMargins(14, 12, 14, 12)
        tag_label = QLabel("TAG")
        tag_label.setStyleSheet("color:#35E6FF;")
        tag_label.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        response_layout.addWidget(tag_label)
        response_text = QLabel("Core systems are online. Memory, voice, tools, and the reasoning loop are ready.")
        response_text.setWordWrap(True)
        response_text.setFont(QFont("Inter", 10))
        response_layout.addWidget(response_text)
        verified = QLabel("LOCAL RESPONSE  •  VERIFIED")
        verified.setStyleSheet("color:#43E09B;")
        verified.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        response_layout.addWidget(verified)
        session_layout.addWidget(response)
        session_layout.addStretch()

        self.orb = OrbWidget()
        session_layout.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignCenter)
        self.state_label = QLabel("READY")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        session_layout.addWidget(self.state_label)
        hint = QLabel("Press Space to talk")
        hint.setProperty("muted", True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setFont(QFont("Inter", 8))
        session_layout.addWidget(hint)
        center_row.addWidget(session, 3)

        runtime = QFrame()
        runtime.setObjectName("Panel")
        runtime_layout = QVBoxLayout(runtime)
        runtime_layout.setContentsMargins(18, 18, 18, 18)
        runtime_title = QLabel("RUNTIME")
        runtime_title.setProperty("muted", True)
        runtime_title.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        runtime_layout.addWidget(runtime_title)

        self.status_rows = {}
        stats = [
            ("Reasoning", "READY", "#43E09B"),
            ("Memory", "ACTIVE", "#43E09B"),
            ("Microphone", "ARMED", "#35E6FF"),
            ("TTS", "READY", "#43E09B"),
            ("Tools", "LOADED", "#35E6FF"),
        ]
        for name, value, color in stats:
            row = QHBoxLayout()
            left = QLabel(name)
            left.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
            right = QLabel(value)
            right.setAlignment(Qt.AlignmentFlag.AlignRight)
            right.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
            right.setStyleSheet(f"color:{color};")
            row.addWidget(left)
            row.addStretch()
            row.addWidget(right)
            runtime_layout.addLayout(row)
            self.status_rows[name] = right

        runtime_layout.addStretch()
        next_box = QFrame()
        next_box.setObjectName("SubPanel")
        next_layout = QVBoxLayout(next_box)
        next_layout.setContentsMargins(12, 10, 12, 10)
        nt = QLabel("NEXT TASK")
        nt.setProperty("muted", True)
        nt.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        nv = QLabel("Awaiting command")
        nv.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        next_layout.addWidget(nt)
        next_layout.addWidget(nv)
        runtime_layout.addWidget(next_box)
        center_row.addWidget(runtime, 1)
        content.addLayout(center_row, 1)

        command = QFrame()
        command.setObjectName("Panel")
        command_layout = QHBoxLayout(command)
        command_layout.setContentsMargins(14, 11, 14, 11)
        command_title = QLabel("COMMAND")
        command_title.setProperty("muted", True)
        command_title.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        command_text = QLabel("Ask TAG anything…")
        command_text.setProperty("muted", True)
        command_text.setFont(QFont("Inter", 10))
        command_layout.addWidget(command_title)
        command_layout.addSpacing(12)
        command_layout.addWidget(command_text)
        command_layout.addStretch()
        self.mic_pill = StatusPill("MIC", "#35E6FF")
        go = QLabel("GO")
        go.setAlignment(Qt.AlignmentFlag.AlignCenter)
        go.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        go.setStyleSheet("color:#0A0D12; background:rgba(53,230,255,210); border-radius:9px; padding:10px 16px;")
        command_layout.addWidget(self.mic_pill)
        command_layout.addSpacing(8)
        command_layout.addWidget(go)
        content.addWidget(command)
        root.addLayout(content, 1)

    def _set_state(self, state: str):
        title, detail, accent = self.STATE_CONFIG.get(state, self.STATE_CONFIG["idle"])
        self.state_label.setText(title)
        self.state_label.setStyleSheet(f"color:{accent};")
        self.orb.set_state(state)
        self.online_label.setText("● ONLINE" if state != "offline" else "● OFFLINE")
        self.online_label.setStyleSheet(f"color:{accent if state == 'offline' else '#43E09B'};")
        self.mic_pill.set_color(accent)
        self.status_rows["Reasoning"].setText(detail if state == "thinking" else "READY")
        self.status_rows["Reasoning"].setStyleSheet(f"color:{accent if state == 'thinking' else '#43E09B'};")
        self.status_rows["Microphone"].setText("CAPTURING" if state == "listening" else "ARMED")
        self.status_rows["Microphone"].setStyleSheet(f"color:{accent if state == 'listening' else '#35E6FF'};")
        self.status_rows["TTS"].setText("OUTPUT" if state == "speaking" else "READY")
        self.status_rows["TTS"].setStyleSheet(f"color:{accent if state == 'speaking' else '#43E09B'};")

    @pyqtSlot(str, str)
    def update_status(self, text: str, state: str):
        """Backend-compatible status update entry point."""
        self._set_state(state)
        if text:
            self.state_label.setText(text.upper())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UltronTopOverlay()
    window.show()
    sys.exit(app.exec())
