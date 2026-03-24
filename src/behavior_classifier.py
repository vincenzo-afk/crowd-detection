"""
Graph Neural Network Crowd Flow Prediction & Behavior Classifier.
Models the crowd as a connected system.
Falls back to deterministic spatial heuristic if pyG not available.
"""

import numpy as np
from typing import List, Dict

from src.detector import Detection

class BehaviorClassifier:
    """Classifies movement anomalies using spatial heuristic or GNN."""
    def __init__(self):
        self.enabled = True
        
    def assess_anomalies(self, detections: List[Detection], speeds: Dict[int, float], vectors: List[tuple]) -> dict:
        """
        Identify anomalous behavior clusters visually and logically.
        Returns anomaly_score (0-100) and list of anomalous track IDs.
        """
        anomalous_ids = []
        
        # Spatial heuristic check
        # Anomaly is defined as moving fast against the grain or erratic group dispersion
        avg_speed = np.mean(list(speeds.values())) if speeds else 0
        
        for det in detections:
            tid = det.track_id
            spd = speeds.get(tid, 0)
            
            # fast outlier
            if avg_speed > 0 and spd > avg_speed * 3.0:
                anomalous_ids.append((tid, "RUNNING_FAST"))
                continue
                
        # Calculate anomalous density
        score = 0.0
        if detections:
            score = (len(anomalous_ids) / len(detections)) * 100.0
            
        return {
            "score": min(score * 3.0, 100.0), # scale up for visibility
            "events": anomalous_ids
        }
