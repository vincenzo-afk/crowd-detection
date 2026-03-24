"""
HUD (Heads-Up Display) renderer.
Draws the full operations dashboard overlay on each video frame.
"""

import cv2
import numpy as np
import time
import psutil
from typing import List, Dict, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    MAX_CAPACITY, ALERT_SAFE, ALERT_WARNING, ALERT_DANGER, ALERT_CRITICAL
)
from src.alerts import LEVEL_COLORS_BGR


class HUDRenderer:
    """Renders all dashboard overlays directly onto the OpenCV frame."""

    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX

    def __init__(self, W: int, H: int):
        self.W = W
        self.H = H
        self._start_time = time.time()
        self._fps_history = []
        self._last_ts = time.time()

    # ── Top status bar ────────────────────────────────────────────────────

    def draw_status_bar(self, frame: np.ndarray, alert_level: str,
                        count: int, density: float,
                        risk_score: float, fps: float) -> np.ndarray:
        color = LEVEL_COLORS_BGR[alert_level]
        # Background bar
        cv2.rectangle(frame, (0, 0), (self.W, 44), (15, 15, 15), -1)
        cv2.rectangle(frame, (0, 0), (self.W, 44), color, 2)

        # Alert pill
        pill_x = 8
        cv2.rectangle(frame, (pill_x, 6), (pill_x + 160, 38), color, -1)
        cv2.putText(frame, f"  {alert_level}", (pill_x + 6, 28),
                    self.FONT_BOLD, 0.7, (0, 0, 0), 2)

        # Stats
        stats = [
            f"People: {count}",
            f"Density: {density*100:.0f}%",
            f"Risk: {risk_score:.0f}%",
            f"FPS: {fps:.1f}",
        ]
        x = pill_x + 175
        for s in stats:
            cv2.putText(frame, s, (x, 27), self.FONT, 0.55, (220, 220, 220), 1)
            x += 160

        # Uptime
        uptime = int(time.time() - self._start_time)
        h_ = uptime // 3600; m_ = (uptime % 3600) // 60; s_ = uptime % 60
        up_str = f"UP {h_:02d}:{m_:02d}:{s_:02d}"
        cv2.putText(frame, up_str, (self.W - 130, 27), self.FONT, 0.5, (150, 150, 150), 1)
        return frame

    # ── Side panel ───────────────────────────────────────────────────────

    def draw_side_panel(self, frame: np.ndarray, metrics: dict,
                         alert_feed: List[dict],
                         predictions: Dict[int, float]) -> np.ndarray:
        panel_w = 240
        panel_x = self.W - panel_w
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, 44), (self.W, self.H), (12, 12, 12), -1)
        frame = cv2.addWeighted(overlay, 0.82, frame, 0.18, 0)

        y = 65
        def txt(text, x=panel_x + 8, color=(200, 200, 200), scale=0.48, thick=1):
            nonlocal y
            cv2.putText(frame, text, (x, y), self.FONT, scale, color, thick)
            y += 20

        def sep():
            nonlocal y
            cv2.line(frame, (panel_x + 4, y), (self.W - 4, y), (50, 50, 50), 1)
            y += 8

        txt("▌ METRICS", color=(100, 200, 255), scale=0.55, thick=2)
        sep()
        txt(f"Count:      {metrics.get('count', 0)}")
        txt(f"Occupancy:  {metrics.get('occupancy_pct', 0)*100:.1f}%")
        txt(f"Capacity:   {MAX_CAPACITY}")
        txt(f"Density:    {metrics.get('density', 0)*100:.1f}%")
        avg_spd = metrics.get('avg_speed', 0)
        txt(f"Avg Speed:  {avg_spd:.1f} px/f")
        mult = metrics.get('speed_multiplier', 1)
        txt(f"Speed Mult: {mult:.2f}x")
        ent = metrics.get('direction_entropy', 1)
        txt(f"Dir. Ent.:  {ent:.2f}")
        comp = "YES ⚠" if metrics.get('compressed') else "No"
        txt(f"Compressed: {comp}", color=(0, 80, 255) if metrics.get('compressed') else (200, 200, 200))
        sd = metrics.get('social_violations', 0)
        txt(f"SD Viol.:   {sd}")

        y += 6
        sep()
        txt("▌ RISK FORECAST", color=(100, 200, 255), scale=0.55, thick=2)
        sep()
        for horizon, val in sorted(predictions.items()):
            bar_w = int((panel_w - 16) * val / 100)
            bar_y = y - 14
            cv2.rectangle(frame, (panel_x + 8, bar_y), (self.W - 8, y + 4), (30, 30, 30), -1)
            c = (0, 200, 80) if val < 40 else (0, 200, 255) if val < 70 else (0, 60, 255)
            cv2.rectangle(frame, (panel_x + 8, bar_y), (panel_x + 8 + bar_w, y + 4), c, -1)
            txt(f"  +{horizon}s: {val:.0f}%", color=(255, 255, 255))

        # Risk trend arrow
        trend = metrics.get("trend", "stable")
        arrow = "↑ rising" if trend == "rising" else "↓ falling" if trend == "falling" else "→ stable"
        arrow_color = (0, 60, 255) if trend == "rising" else (0, 200, 80) if trend == "falling" else (200, 200, 0)
        txt(f"Trend: {arrow}", color=arrow_color)

        y += 6
        sep()
        txt("▌ RECENT ALERTS", color=(100, 200, 255), scale=0.55, thick=2)
        sep()
        alert_colors = {
            ALERT_SAFE: (0, 200, 60), ALERT_WARNING: (0, 200, 255),
            ALERT_DANGER: (0, 100, 255), ALERT_CRITICAL: (0, 0, 230)
        }
        for ev in alert_feed[:5]:
            lvl = ev.get("level", "SAFE")
            msg = ev.get("message", "")[:28]
            t = ev.get("time_str", "")
            txt(f"[{t}] {lvl}", color=alert_colors.get(lvl, (200,200,200)), scale=0.42)
            txt(f"  {msg}", color=(160,160,160), scale=0.38)

        return frame

    # ── Risk gauge ───────────────────────────────────────────────────────

    def draw_risk_gauge(self, frame: np.ndarray, risk_score: float) -> np.ndarray:
        cx, cy = 60, self.H - 60
        radius = 42
        # Background arc
        cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, 180, (40, 40, 40), 8)
        # Coloured arc
        angle = int(risk_score * 1.8)
        c = (0, 200, 80) if risk_score < 40 else (0, 200, 255) if risk_score < 70 else (0, 0, 230)
        cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, angle, c, 8)
        cv2.putText(frame, f"{risk_score:.0f}%", (cx - 20, cy + 6),
                    self.FONT_BOLD, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "RISK", (cx - 14, cy + 22), self.FONT, 0.4, (150, 150, 150), 1)
        return frame

    # ── Alert banner ─────────────────────────────────────────────────────

    def draw_alert_banner(self, frame: np.ndarray, alert_level: str,
                           message: str) -> np.ndarray:
        if alert_level == ALERT_SAFE:
            return frame
        color = LEVEL_COLORS_BGR[alert_level]
        bh = 40
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, self.H - bh - 10), (self.W - 250, self.H - 10), color, -1)
        frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)
        cv2.putText(frame, message[:80], (10, self.H - 22), self.FONT, 0.55, (0, 0, 0), 2)
        return frame

    # ── Trajectory drawing ───────────────────────────────────────────────

    def draw_trajectories(self, frame: np.ndarray,
                           trajectories: Dict[int, list]) -> np.ndarray:
        for tid, traj in trajectories.items():
            if len(traj) < 2:
                continue
            color = tuple((int(c) for c in np.array([
                (tid * 67 % 256), (tid * 131 % 256), (tid * 211 % 256)
            ])))
            for i in range(1, len(traj)):
                alpha = i / len(traj)
                c_ = tuple(int(x * alpha) for x in color)
                cv2.line(frame, traj[i-1], traj[i], c_, 1)
        return frame

    # ── Lost child highlight ──────────────────────────────────────────────

    def draw_lost_child_alerts(self, frame: np.ndarray, lost_children) -> np.ndarray:
        for det in lost_children:
            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), (0, 165, 255), 3)
            cv2.putText(frame, "⚠ LOST CHILD?", (det.x1, det.y1 - 8),
                        self.FONT, 0.6, (0, 165, 255), 2)
        return frame

    # ── System health bar ─────────────────────────────────────────────────

    def draw_system_health(self, frame: np.ndarray, fps: float) -> np.ndarray:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
        except Exception:
            cpu = mem = 0
        y = self.H - 18
        cv2.putText(frame, f"CPU {cpu:.0f}%  MEM {mem:.0f}%  FPS {fps:.1f}",
                    (self.W - 248, 250), self.FONT, 0.38, (100, 100, 100), 1)
        return frame
