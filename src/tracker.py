"""
Multi-Object Tracker using SORT algorithm (Simple Online and Realtime Tracking).
Assigns persistent IDs and maintains trajectory history per person.
"""

import numpy as np
from collections import defaultdict, deque
from typing import List, Dict, Tuple, Optional
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    TRACKER_MAX_AGE, TRACKER_MIN_HITS, TRACKER_IOU_THRESHOLD, TRAJECTORY_HISTORY
)
from src.detector import Detection


class KalmanBoxTracker:
    """Kalman Filter based tracker for a single bounding box."""
    count = 0

    def __init__(self, bbox: Tuple[int, int, int, int]) -> None:
        from filterpy.kalman import KalmanFilter
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        self.kf.F = np.array([
            [1,0,0,0,1,0,0],
            [0,1,0,0,0,1,0],
            [0,0,1,0,0,0,1],
            [0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0],
            [0,0,0,0,0,1,0],
            [0,0,0,0,0,0,1],
        ], dtype=np.float32)
        self.kf.H = np.array([
            [1,0,0,0,0,0,0],
            [0,1,0,0,0,0,0],
            [0,0,1,0,0,0,0],
            [0,0,0,1,0,0,0],
        ], dtype=np.float32)
        self.kf.R[2:, 2:] *= 10.0
        self.kf.P[4:, 4:] *= 1000.0
        self.kf.P *= 10.0
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01
        self.kf.x[:4] = self._bbox_to_z(bbox)

        KalmanBoxTracker.count += 1
        self.id = KalmanBoxTracker.count
        self.hits = 0
        self.hit_streak = 0
        self.age = 0
        self.time_since_update = 0
        self.history: deque = deque(maxlen=TRAJECTORY_HISTORY)

    def _bbox_to_z(self, bbox):
        x1, y1, x2, y2 = bbox
        w = x2 - x1; h = y2 - y1
        x = x1 + w / 2; y = y1 + h / 2
        s = w * h; r = w / float(h) if h else 1.0
        return np.array([[x], [y], [s], [r]], dtype=np.float32)

    def _z_to_bbox(self, z, score=None):
        w = np.sqrt(abs(z[2] * z[3])); h = z[2] / w if w else 0
        x1 = int(z[0] - w / 2); y1 = int(z[1] - h / 2)
        x2 = int(z[0] + w / 2); y2 = int(z[1] + h / 2)
        return x1, y1, x2, y2

    def predict(self):
        if self.kf.x[6] + self.kf.x[2] <= 0:
            self.kf.x[6] *= 0.0
        self.kf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        return self._z_to_bbox(self.kf.x)

    def update(self, bbox):
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        self.kf.update(self._bbox_to_z(bbox))
        center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
        self.history.append(center)

    def get_state(self):
        return self._z_to_bbox(self.kf.x)

    @property
    def center(self):
        state = self.get_state()
        return ((state[0] + state[2]) // 2, (state[1] + state[3]) // 2)


def _iou_batch(bb_test, bb_gt):
    bb_gt_ = np.expand_dims(bb_gt, 0)
    bb_test_ = np.expand_dims(bb_test, 1)
    xx1 = np.maximum(bb_test_[..., 0], bb_gt_[..., 0])
    yy1 = np.maximum(bb_test_[..., 1], bb_gt_[..., 1])
    xx2 = np.minimum(bb_test_[..., 2], bb_gt_[..., 2])
    yy2 = np.minimum(bb_test_[..., 3], bb_gt_[..., 3])
    w = np.maximum(0.0, xx2 - xx1)
    h = np.maximum(0.0, yy2 - yy1)
    inter = w * h
    area_t = (bb_test_[..., 2] - bb_test_[..., 0]) * (bb_test_[..., 3] - bb_test_[..., 1])
    area_g = (bb_gt_[..., 2] - bb_gt_[..., 0]) * (bb_gt_[..., 3] - bb_gt_[..., 1])
    union = area_t + area_g - inter
    return inter / np.where(union == 0, 1e-9, union)


class MultiTracker:
    """SORT multi-object tracker with trajectory history."""

    def __init__(self):
        self.trackers: List[KalmanBoxTracker] = []
        self.frame_count = 0
        self.active_tracks: Dict[int, dict] = {}   # id → metadata
        KalmanBoxTracker.count = 0

    def update(self, detections: List[Detection]) -> List[Detection]:
        """Update tracker with new detections. Returns detections annotated with track IDs."""
        self.frame_count += 1
        dets = np.array([[d.x1, d.y1, d.x2, d.y2] for d in detections], dtype=np.float32) \
               if detections else np.empty((0, 4))

        # Predict all existing tracks
        trks = np.zeros((len(self.trackers), 4))
        to_del = []
        for i, trk in enumerate(self.trackers):
            pos = trk.predict()
            trks[i] = pos
            if np.any(np.isnan(pos)):
                to_del.append(i)
        for i in reversed(to_del):
            self.trackers.pop(i)
            trks = np.delete(trks, i, axis=0)

        matched, unmatched_dets, unmatched_trks = self._associate(dets, trks)

        for m in matched:
            self.trackers[m[1]].update(dets[m[0]])

        for i in unmatched_dets:
            trk = KalmanBoxTracker(dets[i])
            self.trackers.append(trk)

        # Remove dead tracks
        self.trackers = [t for t in self.trackers
                         if t.time_since_update <= TRACKER_MAX_AGE]

        # Build result detections
        result = []
        for trk in self.trackers:
            if trk.hit_streak >= TRACKER_MIN_HITS or self.frame_count <= TRACKER_MIN_HITS:
                state = trk.get_state()
                # Find matching detection for confidence
                conf = 0.9
                for d in detections:
                    if abs(d.cx - trk.center[0]) < 50 and abs(d.cy - trk.center[1]) < 50:
                        conf = d.confidence
                        break
                det = Detection(
                    x1=max(0, state[0]),
                    y1=max(0, state[1]),
                    x2=max(0, state[2]),
                    y2=max(0, state[3]),
                    confidence=conf,
                    track_id=trk.id
                )
                result.append(det)
                self.active_tracks[trk.id] = {
                    "bbox": state,
                    "center": trk.center,
                    "trajectory": list(trk.history),
                    "bbox_height": state[3] - state[1]
                }

        # Prune active_tracks for deleted trackers
        live_ids = {t.id for t in self.trackers}
        self.active_tracks = {k: v for k, v in self.active_tracks.items() if k in live_ids}
        return result

    def _associate(self, dets, trks):
        if len(trks) == 0:
            return np.empty((0, 2), dtype=int), np.arange(len(dets)), np.empty(0, dtype=int)
        if len(dets) == 0:
            return np.empty((0, 2), dtype=int), np.empty(0, dtype=int), np.arange(len(trks))

        iou_mat = _iou_batch(dets, trks)
        if min(iou_mat.shape) > 0:
            row_ind, col_ind = linear_sum_assignment(-iou_mat)
            matched_indices = np.stack([row_ind, col_ind], axis=1)
        else:
            matched_indices = np.empty((0, 2), dtype=int)

        unmatched_dets = [i for i in range(len(dets)) if i not in matched_indices[:, 0]]
        unmatched_trks = [i for i in range(len(trks)) if i not in matched_indices[:, 1]]
        matched = [m for m in matched_indices if iou_mat[m[0], m[1]] >= TRACKER_IOU_THRESHOLD]
        unmatched_dets += [m[0] for m in matched_indices if iou_mat[m[0], m[1]] < TRACKER_IOU_THRESHOLD]
        return np.array(matched), np.array(unmatched_dets), np.array(unmatched_trks)

    def get_trajectories(self) -> Dict[int, list]:
        return {tid: info["trajectory"] for tid, info in self.active_tracks.items()}
