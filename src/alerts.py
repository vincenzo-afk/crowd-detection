"""
Alert Engine — four-level alert system with smart logic, cooldown, and escalation.
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from collections import deque

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    ALERT_SAFE, ALERT_WARNING, ALERT_DANGER, ALERT_CRITICAL,
    ALERT_COOLDOWN_SECONDS, MAX_CAPACITY,
    WARNING_CAPACITY_PCT, DANGER_CAPACITY_PCT
)

LEVEL_ORDER = {ALERT_SAFE: 0, ALERT_WARNING: 1, ALERT_DANGER: 2, ALERT_CRITICAL: 3}

LEVEL_COLORS_BGR = {
    ALERT_SAFE:     (0, 200, 60),
    ALERT_WARNING:  (0, 200, 255),
    ALERT_DANGER:   (0, 100, 255),
    ALERT_CRITICAL: (0, 0, 230)
}

LEVEL_COLORS_HEX = {
    ALERT_SAFE:     "#00c83c",
    ALERT_WARNING:  "#ffc800",
    ALERT_DANGER:   "#ff6400",
    ALERT_CRITICAL: "#e60000"
}


@dataclass
class AlertEvent:
    level: str
    message: str
    timestamp: float = field(default_factory=time.time)
    metrics: dict = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self):
        import datetime
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "time_str": datetime.datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S"),
            "metrics": self.metrics,
            "acknowledged": self.acknowledged
        }


class AlertEngine:
    """
    Aggregates multiple risk signals and produces a single alert level.
    Implements cooldown, priority queue, and callback hooks.
    """

    def __init__(self):
        self.current_level: str = ALERT_SAFE
        self.alert_feed: deque = deque(maxlen=50)
        self._last_alert_time: float = 0
        self._callbacks: List[Callable] = []
        self.risk_score: float = 0.0   # 0–100

    def register_callback(self, fn: Callable):
        """Register a function to be called whenever an alert fires."""
        self._callbacks.append(fn)

    # ── Evaluation ────────────────────────────────────────────────────────

    def evaluate(self, metrics: dict) -> str:
        """
        metrics keys:
            count, density, density_level, speed_level, compressed,
            direction_entropy, occupancy_pct, lost_child, behaviors
        Returns the determined alert level.
        """
        votes = []

        # Density vote
        votes.append(metrics.get("density_level", ALERT_SAFE))

        # Speed vote
        votes.append(metrics.get("speed_level", ALERT_SAFE))

        # Compression
        if metrics.get("compressed", False):
            votes.append(ALERT_DANGER)
            
        if metrics.get("pressure_wave", False):
            votes.append(ALERT_CRITICAL)

        # Cluster merging/density
        dense_clusters = metrics.get("dense_clusters", 0)
        if dense_clusters >= 3:
            votes.append(ALERT_CRITICAL)
        elif dense_clusters >= 1:
            votes.append(ALERT_DANGER)

        # Direction entropy (low entropy = crowd rushing one way)
        entropy = metrics.get("direction_entropy", 1.0)
        if entropy < 0.25:
            votes.append(ALERT_CRITICAL)
        elif entropy < 0.45:
            votes.append(ALERT_DANGER)
        elif entropy < 0.60:
            votes.append(ALERT_WARNING)

        # Occupancy
        occ = metrics.get("occupancy_pct", 0.0)
        if occ >= DANGER_CAPACITY_PCT:
            votes.append(ALERT_DANGER)
        elif occ >= WARNING_CAPACITY_PCT:
            votes.append(ALERT_WARNING)

        # Lost child
        if metrics.get("lost_child", False):
            votes.append(ALERT_WARNING)

        # Tally votes
        counts = {lvl: 0 for lvl in [ALERT_SAFE, ALERT_WARNING, ALERT_DANGER, ALERT_CRITICAL]}
        for v in votes:
            counts[v] = counts.get(v, 0) + 1

        # Critical needs ≥2 signals; Danger needs ≥2
        new_level = ALERT_SAFE
        if counts[ALERT_CRITICAL] >= 2:
            new_level = ALERT_CRITICAL
        elif counts[ALERT_CRITICAL] >= 1 and counts[ALERT_DANGER] >= 1:
            new_level = ALERT_CRITICAL
        elif counts[ALERT_DANGER] >= 2:
            new_level = ALERT_DANGER
        elif counts[ALERT_DANGER] >= 1 or counts[ALERT_WARNING] >= 2:
            new_level = ALERT_WARNING if counts[ALERT_DANGER] == 0 else ALERT_DANGER
        elif counts[ALERT_WARNING] >= 1:
            new_level = ALERT_WARNING

        # Compute risk score 0–100
        self.risk_score = self._compute_risk_score(metrics, new_level)
        self._update_level(new_level, metrics)
        return self.current_level

    def _compute_risk_score(self, metrics: dict, level: str) -> float:
        base = {ALERT_SAFE: 5, ALERT_WARNING: 30, ALERT_DANGER: 65, ALERT_CRITICAL: 90}[level]
        density_bonus = metrics.get("density", 0) * 20
        speed_bonus = min((metrics.get("speed_multiplier", 1) - 1) * 10, 20)
        compression_bonus = 10 if metrics.get("compressed") else 0
        entropy_bonus = (1 - metrics.get("direction_entropy", 1)) * 15
        score = base + density_bonus + speed_bonus + compression_bonus + entropy_bonus
        return float(min(max(score, 0), 100))

    def _update_level(self, new_level: str, metrics: dict):
        level_changed = new_level != self.current_level
        self.current_level = new_level

        now = time.time()
        if level_changed or (LEVEL_ORDER[new_level] >= LEVEL_ORDER[ALERT_WARNING]
                             and now - self._last_alert_time >= ALERT_COOLDOWN_SECONDS):
            if LEVEL_ORDER[new_level] > LEVEL_ORDER[ALERT_SAFE]:
                msg = self._build_message(new_level, metrics)
                event = AlertEvent(level=new_level, message=msg, metrics=metrics)
                self.alert_feed.appendleft(event)
                self._last_alert_time = now
                for cb in self._callbacks:
                    try:
                        cb(event)
                    except Exception as e:
                        print(f"[Alert] Callback error: {e}")

    def _build_message(self, level: str, metrics: dict) -> str:
        parts = []
        d = metrics.get("density", 0)
        if d > 0.1:
            parts.append(f"Density {d*100:.0f}%")
        sm = metrics.get("speed_multiplier", 1)
        if sm > 1.5:
            parts.append(f"Speed {sm:.1f}x baseline")
        if metrics.get("compressed"):
            parts.append("Crowd compression")
        ent = metrics.get("direction_entropy", 1)
        if ent < 0.5:
            parts.append(f"Direction surge ({(1-ent)*100:.0f}% aligned)")
        if metrics.get("lost_child"):
            parts.append("Possible lost child detected")

        detail = " | ".join(parts) if parts else "Multiple metrics elevated"
        prefixes = {
            ALERT_WARNING:  "⚠ WARNING",
            ALERT_DANGER:   "🔶 DANGER",
            ALERT_CRITICAL: "🔴 CRITICAL — STAMPEDE RISK"
        }
        return f"{prefixes.get(level, level)}: {detail}"

    def acknowledge(self, index: int = 0):
        events = list(self.alert_feed)
        if index < len(events):
            events[index].acknowledged = True

    def get_feed(self):
        return [e.to_dict() for e in self.alert_feed]

    def get_color_bgr(self):
        return LEVEL_COLORS_BGR[self.current_level]

    def get_color_hex(self):
        return LEVEL_COLORS_HEX[self.current_level]
