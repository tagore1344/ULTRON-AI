# overlay_ui.py — TRANSPARENT GLASSY EDITION
import customtkinter as ctk
import tkinter as tk
import threading
import time
import math
import random
from config import CONFIG

# ═══════════════════════════════════════════════
#  DATA  –  brain outline as normalised (x, y)
#  points  (0.0 → 1.0  inside the canvas area)
# ═══════════════════════════════════════════════
BRAIN_LEFT = [
    (0.50,0.08),(0.43,0.07),(0.36,0.09),(0.30,0.13),
    (0.24,0.18),(0.19,0.25),(0.16,0.32),(0.15,0.40),
    (0.17,0.48),(0.20,0.55),(0.18,0.62),(0.19,0.69),
    (0.23,0.75),(0.28,0.80),(0.34,0.83),(0.40,0.84),
    (0.46,0.83),(0.50,0.82),
]

BRAIN_RIGHT = [
    (0.50,0.08),(0.57,0.07),(0.64,0.09),(0.70,0.13),
    (0.76,0.18),(0.81,0.25),(0.84,0.32),(0.85,0.40),
    (0.83,0.48),(0.80,0.55),(0.82,0.62),(0.81,0.69),
    (0.77,0.75),(0.72,0.80),(0.66,0.83),(0.60,0.84),
    (0.54,0.83),(0.50,0.82),
]

# Fold / sulci lines (left hemisphere)
FOLDS_LEFT = [
    [(0.35,0.12),(0.30,0.20),(0.26,0.28),(0.27,0.36)],
    [(0.22,0.30),(0.25,0.40),(0.28,0.50),(0.26,0.60)],
    [(0.28,0.55),(0.33,0.63),(0.36,0.72),(0.38,0.80)],
    [(0.42,0.10),(0.40,0.20),(0.38,0.30),(0.35,0.40)],
    [(0.46,0.15),(0.44,0.25),(0.43,0.38),(0.44,0.50)],
]

FOLDS_RIGHT = [
    [(0.65,0.12),(0.70,0.20),(0.74,0.28),(0.73,0.36)],
    [(0.78,0.30),(0.75,0.40),(0.72,0.50),(0.74,0.60)],
    [(0.72,0.55),(0.67,0.63),(0.64,0.72),(0.62,0.80)],
    [(0.58,0.10),(0.60,0.20),(0.62,0.30),(0.65,0.40)],
    [(0.54,0.15),(0.56,0.25),(0.57,0.38),(0.56,0.50)],
]

# Neuron node positions (normalised)
NEURON_POSITIONS = [
    (0.28,0.22),(0.22,0.38),(0.24,0.55),(0.32,0.68),
    (0.42,0.20),(0.38,0.35),(0.35,0.52),(0.40,0.70),
    (0.50,0.15),(0.50,0.45),(0.50,0.72),
    (0.72,0.22),(0.78,0.38),(0.76,0.55),(0.68,0.68),
    (0.58,0.20),(0.62,0.35),(0.65,0.52),(0.60,0.70),
]

# Which neurons are connected
SYNAPSES = [
    (0,1),(1,2),(2,3),(3,7),(4,5),(5,6),(6,7),
    (0,4),(1,5),(2,6),(4,8),(8,9),(9,10),(10,7),
    (11,12),(12,13),(13,14),(15,16),(16,17),(17,18),
    (11,15),(12,16),(13,17),(8,15),(9,16),(10,18),
    (3,10),(14,10),(6,17),(2,13),
]

class Particle:
    """A spark travelling along a synapse."""
    def __init__(self, sx, sy, ex, ey, color):
        self.sx, self.sy = sx, sy
        self.ex, self.ey = ex, ey
        self.color  = color
        self.t      = 0.0
        self.speed  = random.uniform(0.02, 0.05)
        self.size   = random.randint(2, 4)
        self.alive  = True

    def update(self):
        self.t += self.speed
        if self.t >= 1.0:
            self.alive = False

    @property
    def xy(self):
        x = self.sx + (self.ex - self.sx) * self.t
        y = self.sy + (self.ey - self.sy) * self.t
        return x, y

class BrainCanvas:
    """Draws the animated brain on a tk.Canvas."""
    CW = 340
    CH = 260

    STATUS_COLORS = {
        "idle":       "#00d4ff",
        "listening":  "#00ff88",
        "processing": "#ff8800",
        "speaking":   "#ff44aa",
        "error":      "#ff2222",
    }

    def __init__(self, parent):
        self.status  = "idle"
        self.angle   = 0
        self.tick    = 0
        self.glow    = 0.0
        self.glow_d  = 1
        self.particles = []
        self.neuron_fire = [0.0] * len(NEURON_POSITIONS)

        # TRANSPARENT CANVAS
        self.canvas = tk.Canvas(
            parent,
            width=self.CW, height=self.CH,
            bg="#000000", highlightthickness=0
        )
        self.canvas.pack()
        self._running = True
        self._loop()

    def update_status(self, status):
        self.status = status

    def destroy(self):
        self._running = False

    def _col(self):
        return self.STATUS_COLORS.get(self.status, "#00d4ff")

    def _px(self, nx):
        return int(nx * self.CW)

    def _py(self, ny):
        return int(ny * self.CH)

    def _hex_alpha(self, color_hex, alpha):
        """Return a colour string with alpha transparency."""
        r = int(int(color_hex[1:3], 16))
        g = int(int(color_hex[3:5], 16))
        b = int(int(color_hex[5:7], 16))
        return f"#{r:02x}{g:02x}{b:02x}{int(alpha*255):02x}"

    def _draw_brain_outline(self, color, glow_alpha):
        glow_col = self._hex_alpha(color, glow_alpha * 0.3)
        for side in (BRAIN_LEFT, BRAIN_RIGHT):
            pts = []
            for nx, ny in side:
                pts += [self._px(nx), self._py(ny)]
            # Glow layers
            for expand in [6, 3]:
                exp_pts = []
                cx_mid = self._px(0.50)
                cy_mid = self._py(0.45)
                for i in range(0, len(pts), 2):
                    dx = pts[i] - cx_mid
                    dy = pts[i+1] - cy_mid
                    dist = math.hypot(dx, dy) or 1
                    exp_pts += [
                        pts[i] + dx/dist * expand,
                        pts[i+1] + dy/dist * expand,
                    ]
                self.canvas.create_polygon(
                    exp_pts, outline=glow_col,
                    fill="", width=1, smooth=True
                )
            # Solid outline
            self.canvas.create_polygon(
                pts, outline=color,
                fill=self._hex_alpha(color, 0.05),
                width=1, smooth=True
            )

    def _draw_folds(self, color, alpha):
        col = self._hex_alpha(color, alpha * 0.4)
        for fold_set in (FOLDS_LEFT, FOLDS_RIGHT):
            for fold in fold_set:
                pts = []
                for nx, ny in fold:
                    pts += [self._px(nx), self._py(ny)]
                if len(pts) >= 4:
                    self.canvas.create_line(
                        pts, fill=col, width=1,
                        smooth=True, capstyle="round"
                    )

    def _draw_neurons(self, color):
        for i, (nx, ny) in enumerate(NEURON_POSITIONS):
            fire = self.neuron_fire[i]
            if fire < 0.01:
                continue
            cx = self._px(nx)
            cy = self._py(ny)
            # Glow rings
            for ring in range(3, 0, -1):
                ra = fire * 0.2 * (ring / 3)
                rc = self._hex_alpha(color, ra)
                r = ring * 3
                self.canvas.create_oval(
                    cx-r, cy-r, cx+r, cy+r,
                    outline=rc, fill="", width=1
                )
            # Core dot
            core_c = self._hex_alpha(color, min(1.0, fire * 1.2))
            self.canvas.create_oval(
                cx-2, cy-2, cx+2, cy+2,
                fill=core_c, outline=""
            )

    def _draw_synapses(self, color, alpha):
        col = self._hex_alpha(color, alpha * 0.2)
        for a_idx, b_idx in SYNAPSES:
            ax = self._px(NEURON_POSITIONS[a_idx][0])
            ay = self._py(NEURON_POSITIONS[a_idx][1])
            bx = self._px(NEURON_POSITIONS[b_idx][0])
            by = self._py(NEURON_POSITIONS[b_idx][1])
            self.canvas.create_line(ax, ay, bx, by, fill=col, width=1)

    def _draw_particles(self):
        for p in self.particles:
            x, y = p.xy
            s = p.size
            fade = 1.0 - p.t
            c = self._hex_alpha(p.color, fade)
            self.canvas.create_oval(x-s, y-s, x+s, y+s, fill=c, outline="")

    def _draw_idle_wave(self, color):
        wave_r = 30 + 20 * math.sin(math.radians(self.angle * 0.8))
        cx = self._px(0.50)
        cy = self._py(0.45)
        for ring in range(3, 0, -1):
            r = int(wave_r * ring * 0.6)
            a = 0.1 / ring
            col = self._hex_alpha(color, a)
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=col, width=1, fill="")

    def _draw_listening_waves(self, color):
        cx = self._px(0.50)
        cy = self._py(0.45)
        base = 50
        for i in range(4):
            phase = (self.tick * 3 + i * 25) % 100
            r = base + phase * 1.5
            a = max(0.0, 0.4 - phase / 100)
            col = self._hex_alpha(color, a)
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=col, width=1, fill="")

    def _draw_speaking_eq(self, color):
        n = 18
        bw = 6
        gap = 3
        total = n * (bw + gap)
        sx = self._px(0.50) - total // 2
        by = self._py(0.92)
        for i in range(n):
            h = int(5 + 15 * abs(math.sin(math.radians(self.angle * 1.5 + i * 22))))
            x0 = sx + i * (bw + gap)
            col = self._hex_alpha(color, 0.7)
            self.canvas.create_rectangle(x0, by - h, x0 + bw, by, fill=col, outline="")

    def _draw_processing_orbit(self, color):
        cx = self._px(0.50)
        cy = self._py(0.45)
        for i in range(3):
            phase = math.radians(self.angle * 2 + i * 120)
            rx, ry = 100, 75
            ex = cx + rx * math.cos(phase)
            ey = cy + ry * math.sin(phase)
            for t in range(6):
                tp = phase - math.radians(t * 5)
                tx = cx + rx * math.cos(tp)
                ty = cy + ry * math.sin(tp)
                ta = (6-t) / 6 * 0.5
                tc = self._hex_alpha(color, ta)
                ts = max(1, 3 - t // 2)
                self.canvas.create_oval(tx-ts, ty-ts, tx+ts, ty+ts, fill=tc, outline="")
            hc = self._hex_alpha(color, 1.0)
            self.canvas.create_oval(ex-4, ey-4, ex+4, ey+4, fill=hc, outline="")

    def _update_neurons(self):
        status = self.status
        for i in range(len(self.neuron_fire)):
            self.neuron_fire[i] = max(0.0, self.neuron_fire[i] - 0.03)

        if status == "idle" and self.tick % 60 == 0:
            idx = random.randint(0, len(NEURON_POSITIONS)-1)
            self.neuron_fire[idx] = 0.6
        elif status == "listening" and self.tick % 8 == 0:
            for _ in range(random.randint(2, 4)):
                idx = random.randint(0, len(NEURON_POSITIONS)-1)
                self.neuron_fire[idx] = 1.0
        elif status == "processing" and self.tick % 6 == 0:
            idx = (self.tick // 6) % len(NEURON_POSITIONS)
            self.neuron_fire[idx] = 1.0
        elif status == "speaking" and self.tick % 12 == 0:
            for _ in range(3):
                idx = random.randint(0, len(NEURON_POSITIONS)-1)
                self.neuron_fire[idx] = 0.9

    def _spawn_particles(self):
        status = self.status
        color = self._col()
        if status == "idle" and self.tick % 90 == 0 and SYNAPSES:
            a_idx, b_idx = random.choice(SYNAPSES)
            self.particles.append(Particle(
                self._px(NEURON_POSITIONS[a_idx][0]),
                self._py(NEURON_POSITIONS[a_idx][1]),
                self._px(NEURON_POSITIONS[b_idx][0]),
                self._py(NEURON_POSITIONS[b_idx][1]),
                color
            ))
        elif status == "listening" and self.tick % 15 == 0:
            for _ in range(2):
                a_idx, b_idx = random.choice(SYNAPSES)
                self.particles.append(Particle(
                    self._px(NEURON_POSITIONS[a_idx][0]),
                    self._py(NEURON_POSITIONS[a_idx][1]),
                    self._px(NEURON_POSITIONS[b_idx][0]),
                    self._py(NEURON_POSITIONS[b_idx][1]),
                    color
                ))
        elif status == "processing" and self.tick % 8 == 0:
            for _ in range(3):
                a_idx, b_idx = random.choice(SYNAPSES)
                self.particles.append(Particle(
                    self._px(NEURON_POSITIONS[a_idx][0]),
                    self._py(NEURON_POSITIONS[a_idx][1]),
                    self._px(NEURON_POSITIONS[b_idx][0]),
                    self._py(NEURON_POSITIONS[b_idx][1]),
                    color
                ))
        elif status == "speaking" and self.tick % 12 == 0:
            for _ in range(2):
                a_idx, b_idx = random.choice(SYNAPSES)
                self.particles.append(Particle(
                    self._px(NEURON_POSITIONS[a_idx][0]),
                    self._py(NEURON_POSITIONS[a_idx][1]),
                    self._px(NEURON_POSITIONS[b_idx][0]),
                    self._py(NEURON_POSITIONS[b_idx][1]),
                    color
                ))
        self.particles = [p for p in self.particles if p.alive]
        if len(self.particles) > 50:
            self.particles = self.particles[-50:]

    def _update_glow(self):
        speed = {
            "idle": 0.01, "listening": 0.03,
            "processing": 0.03, "speaking": 0.025,
            "error": 0.05,
        }.get(self.status, 0.015)
        self.glow += speed * self.glow_d
        if self.glow >= 1.0:
            self.glow = 1.0
            self.glow_d = -1
        elif self.glow <= 0.2:
            self.glow = 0.2
            self.glow_d = 1

    def _render(self):
        self.canvas.delete("all")
        color = self._col()
        g = self.glow
        self._draw_brain_outline(color, g)
        self._draw_folds(color, g)
        syn_a = 0.15 + 0.35 * g
        if self.status in ("processing","listening"):
            syn_a = min(1.0, syn_a * 2)
        self._draw_synapses(color, syn_a)

        if self.status == "idle":
            self._draw_idle_wave(color)
        elif self.status == "listening":
            self._draw_listening_waves(color)
        elif self.status == "processing":
            self._draw_processing_orbit(color)
        elif self.status == "speaking":
            self._draw_speaking_eq(color)

        self._draw_neurons(color)
        self._draw_particles()

        div_col = self._hex_alpha(color, 0.3)
        self.canvas.create_line(
            self._px(0.50), self._py(0.08),
            self._px(0.50), self._py(0.82),
            fill=div_col, width=1, dash=(4,4)
        )

    def _loop(self):
        if not self._running:
            return
        self._update_glow()
        self._update_neurons()
        self._spawn_particles()
        for p in self.particles:
            p.update()
        self._render()
        self.angle = (self.angle + 3) % 360
        self.tick = (self.tick + 1) % 10000
        self.canvas.after(25, self._loop)

class AssistantOverlay:
    def __init__(self, on_close_callback=None):
        self.on_close = on_close_callback
        self.brain = None
        self._build_window()

    def _build_window(self):
        ctk.set_appearance_mode("dark")

        self.root = ctk.CTk()
        self.root.title("ULTRON")
        self.root.attributes('-topmost', True)
        
        # ═══ TRANSPARENT WINDOW ═══
        self.root.attributes('-transparentcolor', '#000000')
        self.root.attributes('-alpha', 0.85)
        self.root.overrideredirect(True)

        W, H = 360, 420
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - W - 20
        y = sh - H - 60
        self.root.geometry(f"{W}x{H}+{x}+{y}")

        # ── TRANSPARENT FRAME ──
        self.frame = ctk.CTkFrame(
            self.root,
            fg_color="#000000",
            corner_radius=20,
            border_width=1,
            border_color="#00d4ff"
        )
        self.frame.pack(fill="both", expand=True, padx=1, pady=1)

        # ── HEADER ──
        hdr = ctk.CTkFrame(self.frame, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10,0))

        self.title_lbl = ctk.CTkLabel(
            hdr,
            text=f"⚡ {CONFIG['assistant_name']}",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color="#00d4ff"
        )
        self.title_lbl.pack(side="left")

        # Minimize button
        ctk.CTkButton(
            hdr, text="─", width=24, height=20,
            command=self._minimize,
            fg_color="transparent",
            hover_color="#1a1a2e",
            text_color="#555566",
            font=ctk.CTkFont(size=11)
        ).pack(side="right", padx=(4,0))

        # ── BRAIN CANVAS ──
        brain_frame = ctk.CTkFrame(
            self.frame,
            fg_color="#000000",
            corner_radius=12
        )
        brain_frame.pack(padx=10, pady=8)

        self.brain = BrainCanvas(brain_frame)

        # ── STATUS ROW ──
        status_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        status_row.pack(fill="x", padx=14)

        self.dot_lbl = ctk.CTkLabel(
            status_row, text="●",
            font=ctk.CTkFont(size=10),
            text_color="#00d4ff"
        )
        self.dot_lbl.pack(side="left")

        self.status_lbl = ctk.CTkLabel(
            status_row,
            text="IDLE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#00d4ff"
        )
        self.status_lbl.pack(side="left", padx=(4,0))

        # ── COMMAND TEXT ──
        self.cmd_lbl = ctk.CTkLabel(
            self.frame,
            text=f"Say  \"{CONFIG['wake_words'][0]}\"  to activate",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#3a3a5a",
            wraplength=320
        )
        self.cmd_lbl.pack(padx=14, pady=(4,12))

        # ── DRAGGABLE ──
        self._dx = self._dy = 0
        for widget in (self.frame, hdr, self.title_lbl):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag)

        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag(self, e):
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def update_status(self, status, text=""):
        colors = {
            "idle":       "#00d4ff",
            "listening":  "#00ff88",
            "processing": "#ff8800",
            "speaking":   "#ff44aa",
            "error":      "#ff2222",
        }
        labels = {
            "idle":       "IDLE",
            "listening":  "LISTENING...",
            "processing": "PROCESSING...",
            "speaking":   "SPEAKING...",
            "error":      "ERROR",
        }
        color = colors.get(status, "#00d4ff")

        if self.brain:
            self.brain.update_status(status)

        def _update():
            try:
                self.status_lbl.configure(
                    text=labels.get(status, "IDLE"),
                    text_color=color
                )
                self.dot_lbl.configure(text_color=color)
                self.frame.configure(border_color=color)
                if text:
                    self.cmd_lbl.configure(
                        text=text,
                        text_color="#888899" if status != "idle" else "#3a3a5a"
                    )
            except:
                pass

        try:
            self.root.after(0, _update)
        except:
            pass

    def _minimize(self):
        self.root.overrideredirect(False)
        self.root.iconify()

    def _close(self):
        if self.brain:
            self.brain.destroy()
        if self.on_close:
            self.on_close()
        try:
            self.root.quit()
        except:
            pass

    def run(self):
        self.root.mainloop()