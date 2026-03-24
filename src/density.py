"""
Crowd Density Analysis Module.
Computes global density, zone-based density grid, heatmaps, and occupancy stats.
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict
from collections import deque

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    DENSITY_GRID_ROWS, DENSITY_GRID_COLS,
    DENSITY_WARNING, DENSITY_DANGER, DENSITY_CRITICAL,
    MAX_CAPACITY, WARNING_CAPACITY_PCT, DANGER_CAPACITY_PCT,
    ALERT_SAFE, ALERT_WARNING, ALERT_DANGER, ALERT_CRITICAL,
    HEATMAP_DECAY
)
from src.detector import Detection


class DensityAnalyzer:
    """Computes density metrics from detections."""

    def __init__(self, frame_width: int, frame_height: int):
        self.W = frame_width
        self.H = frame_height
        self.total_pixels = frame_width * frame_height

        self.heatmap = np.zeros((frame_height, frame_width), dtype=np.float32)
        self.motion_heatmap = np.zeros((frame_height, frame_width), dtype=np.float32)

        self.count_history: deque = deque(maxlen=120)
        self.density_history: deque = deque(maxlen=120)
        self.peak_count = 0
        self.peak_density = 0.0
        self.in_count = 0
        self.out_count = 0

    # ── Density ──────────────────────────────────────────────────────────────

    def compute_global_density(self, detections: List[Detection]) -> float:
        """Normalised density score (0–1) based on person bounding-box area."""
        if not detections or self.total_pixels == 0:
            return 0.0
        total_area = sum(d.area for d in detections)
        return min(total_area / (self.total_pixels * 0.5), 1.0)

    def get_density_level(self, density: float) -> str:
        if density >= DENSITY_CRITICAL:
            return ALERT_CRITICAL
        if density >= DENSITY_DANGER:
            return ALERT_DANGER
        if density >= DENSITY_WARNING:
            return ALERT_WARNING
        return ALERT_SAFE

    # ── Zone Grid ────────────────────────────────────────────────────────────

    def compute_zone_density(self, detections: List[Detection]) -> List[List[dict]]:
        """
        Divide the frame into ROWS × COLS zones.
        Each cell: {'count': int, 'density': float, 'risk': str}
        """
        cell_w = self.W / DENSITY_GRID_COLS
        cell_h = self.H / DENSITY_GRID_ROWS
        grid = [[{"count": 0, "density": 0.0, "risk": ALERT_SAFE}
                  for _ in range(DENSITY_GRID_COLS)]
                 for _ in range(DENSITY_GRID_ROWS)]

        for det in detections:
            col = min(int(det.cx / cell_w), DENSITY_GRID_COLS - 1)
            row = min(int(det.cy / cell_h), DENSITY_GRID_ROWS - 1)
            grid[row][col]["count"] += 1

        cell_area = cell_w * cell_h
        for row in range(DENSITY_GRID_ROWS):
            for col in range(DENSITY_GRID_COLS):
                c = grid[row][col]["count"]
                d = (c * 2500) / cell_area if cell_area > 0 else 0
                d = min(d, 1.0)
                grid[row][col]["density"] = d
                grid[row][col]["risk"] = self.get_density_level(d)
        return grid

    # ── Heatmap ───────────────────────────────────────────────────────────────

    def update_heatmap(self, detections: List[Detection]) -> np.ndarray:
        """Update and return the density heatmap."""
        self.heatmap *= HEATMAP_DECAY
        for det in detections:
            cx, cy = det.cx, det.cy
            r = max(det.height // 3, 20)
            x1 = max(0, cx - r); y1 = max(0, cy - r)
            x2 = min(self.W, cx + r); y2 = min(self.H, cy + r)
            self.heatmap[y1:y2, x1:x2] += 0.5
        self.heatmap = np.clip(self.heatmap, 0, 15)
        return self.heatmap

    def update_motion_heatmap(self, prev_centers: Dict[int, tuple],
                               curr_centers: Dict[int, tuple]) -> np.ndarray:
        self.motion_heatmap *= HEATMAP_DECAY
        for tid, curr in curr_centers.items():
            if tid in prev_centers:
                prev = prev_centers[tid]
                dist = np.hypot(curr[0] - prev[0], curr[1] - prev[1])
                if dist > 2:
                    cx, cy = curr
                    r = 20
                    x1 = max(0, cx - r); y1 = max(0, cy - r)
                    x2 = min(self.W, cx + r); y2 = min(self.H, cy + r)
                    self.motion_heatmap[y1:y2, x1:x2] += dist * 0.05
        self.motion_heatmap = np.clip(self.motion_heatmap, 0, 15)
        return self.motion_heatmap

    def render_heatmap_overlay(self, frame: np.ndarray,
                                heatmap: np.ndarray, alpha: float = 0.5) -> np.ndarray:
        norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX)
        norm = norm.astype(np.uint8)
        colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        mask = norm > 10
        overlay = frame.copy()
        overlay[mask] = cv2.addWeighted(frame, 1 - alpha, colored, alpha, 0)[mask]
        return overlay

    # ── Occupancy / Count ────────────────────────────────────────────────────

    def update_counts(self, count: int, density: float):
        self.count_history.append(count)
        self.density_history.append(density)
        if count > self.peak_count:
            self.peak_count = count
        if density > self.peak_density:
            self.peak_density = density

    def get_occupancy_pct(self, count: int) -> float:
        return min(count / max(MAX_CAPACITY, 1), 1.0)

    def get_rolling_avg_count(self) -> float:
        return np.mean(self.count_history) if self.count_history else 0

    # ── Zone Grid Overlay ────────────────────────────────────────────────────

    def draw_zone_grid(self, frame: np.ndarray,
                        zone_grid: List[List[dict]]) -> np.ndarray:
        cell_w = self.W // DENSITY_GRID_COLS
        cell_h = self.H // DENSITY_GRID_ROWS
        colors = {
            ALERT_SAFE: (0, 200, 0),
            ALERT_WARNING: (0, 200, 255),
            ALERT_DANGER: (0, 140, 255),
            ALERT_CRITICAL: (0, 0, 220)
        }
        overlay = frame.copy()
        for r in range(DENSITY_GRID_ROWS):
            for c in range(DENSITY_GRID_COLS):
                zone = zone_grid[r][c]
                x1 = c * cell_w; y1 = r * cell_h
                x2 = x1 + cell_w; y2 = y1 + cell_h
                color = colors.get(zone["risk"], (128, 128, 128))
                if zone["count"] > 0:
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 1)
        frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)
        for r in range(DENSITY_GRID_ROWS):
            for c in range(DENSITY_GRID_COLS):
                zone = zone_grid[r][c]
                if zone["count"] > 0:
                    x = c * cell_w + 4; y = r * cell_h + 14
                    cv2.putText(frame, str(zone["count"]), (x, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        return frame
