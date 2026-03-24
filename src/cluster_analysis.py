"""
Group and Cluster Analysis.
Detects tight clusters of people forming using spatial proximity (DBSCAN equivalent logic).
Flags clusters that are too tight (merging risk).
"""

from typing import List, Dict, Tuple, Any
import numpy as np

from src.detector import Detection

class ClusterAnalyzer:
    def __init__(self, cluster_radius: int = 40):
        self.cluster_radius = cluster_radius
        
    def analyze(self, detections: List[Detection]) -> Dict[str, Any]:
        """
        Groups bounding boxes by proximity.
        Returns cluster groups and flags any critically dense clusters.
        """
        if not detections:
            return {"clusters": [], "dense_clusters": 0}
            
        points = np.array([[d.cx, d.cy] for d in detections])
        # Simple greedy O(N^2) clustering for brevity, DBSCAN is better suited for prod.
        n = len(points)
        assigned = [False] * n
        clusters = []
        
        for i in range(n):
            if assigned[i]:
                continue
            
            cluster = [i]
            assigned[i] = True
            
            # Find all neighbors recursively
            queue = [i]
            while queue:
                curr = queue.pop(0)
                for j in range(n):
                    if not assigned[j]:
                        dist = np.hypot(points[curr][0]-points[j][0], points[curr][1]-points[j][1])
                        if dist < self.cluster_radius:
                            assigned[j] = True
                            cluster.append(j)
                            queue.append(j)
            
            if len(cluster) > 1:
                clusters.append([detections[k] for k in cluster])
                
        # Count dense clusters (clusters with > 6 people in a very small radius)
        dense_clusters = 0
        for c in clusters:
            if len(c) > 6:
                # Assess bounding box density
                c_points = np.array([[d.cx, d.cy] for d in c])
                max_d = np.max(np.linalg.norm(c_points - np.mean(c_points, axis=0), axis=1))
                if max_d < self.cluster_radius * 1.5:
                    dense_clusters += 1
                    
        return {
            "clusters": clusters,
            "dense_clusters": dense_clusters,
            "total_clusters": len(clusters)
        }
