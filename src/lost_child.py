"""
Lost Child Detection Module.
Flags isolated small figures that may be separated children.
"""

import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
import numpy as np

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    CHILD_BBOX_HEIGHT_RATIO, CHILD_ALONE_SECONDS, CHILD_PROXIMITY_RADIUS
)
from src.detector import Detection


class LostChildDetector:
    def __init__(self):
        self._alone_since: Dict[int, float] = {}   # track_id → time first seen alone
        self._flagged: Dict[int, float] = {}        # track_id → time alert fired

    def update(self, detections: List[Detection]) -> List[Detection]:
        """Returns list of detections flagged as potential lost children."""
        if not detections:
            self._alone_since.clear()
            return []

        # Estimate adult avg height
        heights = [d.height for d in detections]
        avg_h = np.percentile(heights, 75) if heights else 100

        # Classify each person
        children = [d for d in detections if d.height < avg_h * CHILD_BBOX_HEIGHT_RATIO]
        adults = [d for d in detections if d not in children]

        lost = []
        now = time.time()
        seen_ids = set()

        for child in children:
            # Check proximity to any adult
            nearby_adult = any(
                abs(child.cx - a.cx) < CHILD_PROXIMITY_RADIUS
                and abs(child.cy - a.cy) < CHILD_PROXIMITY_RADIUS
                for a in adults
            )
            
            seen_ids.add(child.track_id)
            
            if nearby_adult:
                self._alone_since.pop(child.track_id, None)
                continue

            if child.track_id not in self._alone_since:
                self._alone_since[child.track_id] = {"time": now, "pos": (child.cx, child.cy), "stationary": False}

            tracker = self._alone_since[child.track_id]
            elapsed = now - tracker["time"]
            
            # Check stationary condition:
            ox, oy = tracker["pos"]
            dist_moved = np.hypot(child.cx - ox, child.cy - oy)
            if dist_moved < 20 and elapsed > (CHILD_ALONE_SECONDS * 0.5):
                tracker["stationary"] = True
                
            # If alone too long, or stationary and alone for moderate duration
            if elapsed >= CHILD_ALONE_SECONDS or tracker["stationary"]:
                lost.append(child)

        # Remove stale entries
        for tid in list(self._alone_since.keys()):
            if tid not in seen_ids:
                self._alone_since.pop(tid, None)

        return lost
