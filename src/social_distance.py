"""
Social Distance Monitor — measures inter-person distances and flags violations.
"""

import numpy as np
import cv2
from typing import List, Tuple

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SOCIAL_DISTANCE_PX
from src.detector import Detection


class SocialDistanceMonitor:
    def __init__(self, min_distance_px: int = SOCIAL_DISTANCE_PX):
        self.min_distance = min_distance_px
        self.total_violations = 0
        self.current_violations = 0

    def compute_violations(self, detections: List[Detection]) -> List[Tuple[Detection, Detection]]:
        """Returns pairs of detections that are too close."""
        violations = []
        for i in range(len(detections)):
            for j in range(i + 1, len(detections)):
                a = detections[i]; b = detections[j]
                dist = np.hypot(a.cx - b.cx, a.cy - b.cy)
                if dist < self.min_distance:
                    violations.append((a, b))
        self.current_violations = len(violations)
        self.total_violations += len(violations)
        return violations

    def draw_violations(self, frame: np.ndarray,
                         violations: List[Tuple[Detection, Detection]]) -> np.ndarray:
        for a, b in violations:
            cv2.line(frame, a.center, b.center, (0, 0, 255), 1)
            cv2.circle(frame, a.center, 6, (0, 0, 255), -1)
            cv2.circle(frame, b.center, 6, (0, 0, 255), -1)
        return frame
