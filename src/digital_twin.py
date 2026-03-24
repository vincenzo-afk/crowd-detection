"""
Digital Twin module.
Manages a 2D spatial representation of the crowd, maps real coordinates
to the venue layout, and simulates simple forward-trajectories.
"""

from typing import List, Dict, Any
from src.detector import Detection
from config.settings import DEFAULT_SOURCE

class DigitalTwin:
    def __init__(self, venue_name: str = "Main Hub", width: int = 1280, height: int = 720):
        self.venue_name = venue_name
        self.venue_w = width
        self.venue_h = height
        self.entities = {} # track_id -> {x, y, vx, vy, speed}
        # In a real system, we map camera perspective to overhead map.
        
    def update(self, detections: List[Detection], speeds: Dict[int, float], vectors: List[tuple]) -> dict:
        """Update the digital twin state from active detections."""
        new_entities = {}
        for det in detections:
            tid = det.track_id
            cx, cy = det.cx, det.cy
            speed = speeds.get(tid, 0.0)
            
            # basic vector matching
            vx, vy = 0.0, 0.0
            for start, end in vectors:
                if start == (cx, cy):
                    vx, vy = (end[0]-cx)/3.0, (end[1]-cy)/3.0 # scale back
                    break
            
            new_entities[tid] = {
                "x": cx,
                "y": cy,
                "vx": vx,
                "vy": vy,
                "speed": speed
            }
            
        self.entities = new_entities
        return self._generate_simulated_future()
        
    def _generate_simulated_future(self, steps=30):
        """Simulate forward trajectories for 30 ticks to find bottlenecks (Digital Twin simulation)"""
        future_state = {}
        for tid, data in self.entities.items():
            fx = data["x"] + data["vx"] * steps
            fy = data["y"] + data["vy"] * steps
            future_state[tid] = {"x": fx, "y": fy}
        
        return future_state
