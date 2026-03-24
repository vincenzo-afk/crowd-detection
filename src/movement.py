"""
Movement & Speed Analysis Module.
Tracks per-person speed, crowd flow direction, flow vectors,
and detects stampede pre-indicators.
"""

from scipy.spatial.distance import cdist
import numpy as np
import cv2
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    SPEED_WINDOW, SPEED_WARNING_MULTIPLIER, SPEED_DANGER_MULTIPLIER,
    MIN_DISTANCE_BETWEEN_PEOPLE, ALERT_SAFE, ALERT_WARNING, ALERT_DANGER, ALERT_CRITICAL
)
from src.detector import Detection


class MovementAnalyzer:
    """Analyses per-person and crowd-level movement."""

    def __init__(self):
        self.speed_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=SPEED_WINDOW))
        self.position_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=30))
        self.direction_history: deque = deque(maxlen=60)
        self.avg_speed_history: deque = deque(maxlen=60)
        self.baseline_speed: Optional[float] = None
        self._baseline_samples: deque = deque(maxlen=120)

    # ── Speed ──────────────────────────────────────────────────────────────

    def update(self, detections: List[Detection]) -> Dict[int, float]:
        """Update positions; return dict{track_id: speed_px_per_frame}."""
        speeds = {}
        for det in detections:
            tid = det.track_id
            cx, cy = det.cx, det.cy
            history = self.position_history[tid]
            if history:
                prev = history[-1]
                spd = float(np.hypot(cx - prev[0], cy - prev[1]))
            else:
                spd = 0.0
            self.position_history[tid].append((cx, cy))
            self.speed_history[tid].append(spd)
            speeds[tid] = spd
        return speeds

    def get_avg_speed(self, speeds: Dict[int, float]) -> float:
        if not speeds:
            return 0.0
        return float(np.mean(list(speeds.values())))

    def get_person_avg_speed(self, track_id: int) -> float:
        h = self.speed_history.get(track_id)
        return float(np.mean(h)) if h else 0.0

    def update_baseline(self, avg_speed: float):
        self._baseline_samples.append(avg_speed)
        self.avg_speed_history.append(avg_speed)
        if len(self._baseline_samples) >= 30 and self.baseline_speed is None:
            self.baseline_speed = float(np.mean(self._baseline_samples))
        elif self.baseline_speed is not None:
            # Slowly drift baseline
            self.baseline_speed = self.baseline_speed * 0.99 + avg_speed * 0.01

    def get_speed_multiplier(self, avg_speed: float) -> float:
        if self.baseline_speed and self.baseline_speed > 0:
            return avg_speed / self.baseline_speed
        return 1.0

    def detect_speed_spike(self, avg_speed: float) -> str:
        mult = self.get_speed_multiplier(avg_speed)
        if mult >= SPEED_DANGER_MULTIPLIER:
            return ALERT_CRITICAL
        if mult >= SPEED_WARNING_MULTIPLIER:
            return ALERT_WARNING
        return ALERT_SAFE

    # ── Direction Entropy ─────────────────────────────────────────────────

    def compute_direction_entropy(self, detections: List[Detection]) -> float:
        """
        0 = everyone moving same direction (high risk),
        1 = fully chaotic (normal social scenario).
        """
        angles = []
        for det in detections:
            tid = det.track_id
            hist = self.position_history.get(tid)
            if hist and len(hist) >= 2:
                dx = hist[-1][0] - hist[-2][0]
                dy = hist[-1][1] - hist[-2][1]
                if abs(dx) + abs(dy) > 1:
                    angles.append(np.arctan2(dy, dx))
        if len(angles) < 3:
            return 1.0
        bins = np.histogram(angles, bins=8, range=(-np.pi, np.pi))[0]
        probs = bins / bins.sum()
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs)) / np.log2(8)
        return float(np.clip(entropy, 0, 1))

    # ── Crowd Compression ─────────────────────────────────────────────────

    def detect_compression(self, detections: List[Detection]) -> Tuple[bool, float, bool]:
        """
        Returns (is_compressed, avg_inter_person_distance, is_pressure_wave).
        Tracks frame-by-frame compression deltas to map pressure wave events.
        """
        if len(detections) < 2:
            return False, 9999.0, False
            
        centers = np.array([(d.cx, d.cy) for d in detections], dtype=np.float32)
        dists = cdist(centers, centers)
        np.fill_diagonal(dists, np.inf)
        min_dists = dists.min(axis=1)
        
        avg_min_dist = float(np.mean(min_dists))
        compressed = avg_min_dist < MIN_DISTANCE_BETWEEN_PEOPLE
        
        # Pressure Wave Tracking
        # Checks if average distance is dropping sharply while staying within hazard bounds
        wave_detected = False
        if not hasattr(self, '_compression_history'):
            self._compression_history = deque(maxlen=10)
        self._compression_history.append(avg_min_dist)
        
        if len(self._compression_history) == self._compression_history.maxlen:
            # Drop in distance over the past N frames indicating rapid compression spread
            dist_drop = self._compression_history[0] - self._compression_history[-1]
            if dist_drop > (MIN_DISTANCE_BETWEEN_PEOPLE * 0.4) and avg_min_dist < MIN_DISTANCE_BETWEEN_PEOPLE * 1.5:
                wave_detected = True

        return compressed, avg_min_dist, wave_detected

    # ── Flow Vectors ──────────────────────────────────────────────────────

    def compute_flow_vectors(self, detections: List[Detection],
                              scale: float = 3.0) -> List[Tuple]:
        """Returns list of (start_point, end_point) for flow arrows."""
        vectors = []
        for det in detections:
            tid = det.track_id
            hist = self.position_history.get(tid)
            if hist and len(hist) >= 3:
                xs = [p[0] for p in list(hist)[-5:]]
                ys = [p[1] for p in list(hist)[-5:]]
                dx = (xs[-1] - xs[0]) * scale
                dy = (ys[-1] - ys[0]) * scale
                start = (det.cx, det.cy)
                end = (int(det.cx + dx), int(det.cy + dy))
                vectors.append((start, end))
        return vectors

    def draw_flow_arrows(self, frame: np.ndarray,
                          vectors: List[Tuple]) -> np.ndarray:
        for start, end in vectors:
            dx = end[0] - start[0]; dy = end[1] - start[1]
            mag = np.hypot(dx, dy)
            if mag < 3:
                continue
            color = (0, 200, 255)
            cv2.arrowedLine(frame, start, end, color, 2, tipLength=0.3)
        return frame

    # ── Behavior Detection ────────────────────────────────────────────────

    def detect_behaviors(self, detections: List[Detection],
                          avg_speed: float) -> Dict[int, List[str]]:
        behaviors: Dict[int, List[str]] = defaultdict(list)
        for det in detections:
            tid = det.track_id
            spd = self.get_person_avg_speed(tid)

            # Running
            if avg_speed > 0 and spd > avg_speed * 2.5:
                behaviors[tid].append("RUNNING")

            # Loitering (stationary while crowd moves)
            if avg_speed > 3 and spd < 1.0:
                behaviors[tid].append("LOITERING")

            # Erratic movement
            hist = self.position_history.get(tid)
            if hist and len(hist) >= 8:
                recent = list(hist)[-8:]
                angles = []
                for i in range(1, len(recent)):
                    dx = recent[i][0] - recent[i-1][0]
                    dy = recent[i][1] - recent[i-1][1]
                    if abs(dx) + abs(dy) > 2:
                        angles.append(np.arctan2(dy, dx))
                if len(angles) >= 3:
                    diffs = [abs(angles[i] - angles[i-1]) for i in range(1, len(angles))]
                    if np.mean(diffs) > 1.5:
                        behaviors[tid].append("ERRATIC")

            # Falling (bbox becomes landscape)
            w = det.width; h = det.height
            if h > 0 and w / h > 1.8:
                behaviors[tid].append("FALLING")

        return dict(behaviors)
