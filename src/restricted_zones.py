"""
Restricted Zone Enforcement Module.
Verifies whether any trackers intrude designated "restricted polygons". 
"""

import cv2
import numpy as np
from typing import List, Dict

from src.detector import Detection
from src.zone_manager import ZoneManager

class RestrictedZoneEnforcer:
    def __init__(self, zone_manager: ZoneManager):
        self.zm = zone_manager
        
    def assess_intrusions(self, detections: List[Detection]) -> Dict[str, List[int]]:
        """
        Check if the center-point of any detection resides inside a restricted zone.
        Returns mapping of zone_name to intruding track_ids.
        """
        intrusions = {}
        target_zones = self.zm.get_all()
        
        if not target_zones:
            return intrusions
            
        for name, points in target_zones.items():
            poly = np.array(points, np.int32)
            for det in detections:
                cx, cy = det.cx, det.cy
                # cv2.pointPolygonTest returns > 0 if inside, 0 on edge, < 0 outside
                if cv2.pointPolygonTest(poly, (cx, cy), False) >= 0:
                    if name not in intrusions:
                        intrusions[name] = []
                    intrusions[name].append(det.track_id)
                    
        return intrusions
        
    def get_violation_count(self, detections: List[Detection]) -> int:
        d = self.assess_intrusions(detections)
        return sum([len(v) for v in d.values()])
