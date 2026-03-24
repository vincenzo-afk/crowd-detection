"""
YOLOv8 Person Detector
Detects people in each frame and returns bounding-box results.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    YOLO_MODEL, YOLO_CONFIDENCE, YOLO_IOU_THRESHOLD, YOLO_CLASSES, MODEL_DIR
)


@dataclass
class Detection:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    track_id: int = -1

    @property
    def cx(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def cy(self) -> int:
        return (self.y1 + self.y2) // 2

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def bbox(self):
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def center(self):
        return (self.cx, self.cy)


class PersonDetector:
    """Wraps YOLOv8 for real-time person detection."""

    def __init__(self, model_name: str = YOLO_MODEL):
        self.model = None
        self.model_name = model_name
        self.frame_count = 0
        self.total_detections = 0
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            model_path = os.path.join(MODEL_DIR, self.model_name)
            # Download to models dir if not there
            if not os.path.exists(model_path):
                model_path = self.model_name   # ultralytics auto-downloads
            self.model = YOLO(model_path)
            print(f"[Detector] Model loaded: {self.model_name}")
        except Exception as e:
            print(f"[Detector] WARNING: Could not load YOLO model ({e}). Using simulation.")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run inference on a single frame. Returns list of Detection objects."""
        self.frame_count += 1
        if self.model is None:
            return []

        try:
            results = self.model(
                frame,
                conf=YOLO_CONFIDENCE,
                iou=YOLO_IOU_THRESHOLD,
                classes=YOLO_CLASSES,
                verbose=False
            )
            detections = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = float(box.conf[0])
                    detections.append(Detection(x1, y1, x2, y2, conf))
            self.total_detections += len(detections)
            return detections
        except Exception as e:
            print(f"[Detector] Inference error: {e}")
            return []

    def draw_detections(self, frame: np.ndarray, detections: List[Detection],
                        show_confidence: bool = True, blur_faces: bool = True) -> np.ndarray:
        """Draw bounding boxes on frame with optional privacy face blurring."""
        for det in detections:
            # Privacy: Blur top 20% of bounding box (approx head location)
            if blur_faces:
                head_h = int(det.height * 0.25)
                hx1, hy1, hx2, hy2 = det.x1, det.y1, det.x2, det.y1 + head_h
                
                # Bounds check
                hx1, hy1 = max(0, hx1), max(0, hy1)
                hx2, hy2 = min(frame.shape[1], hx2), min(frame.shape[0], hy2)
                
                if hx2 > hx1 and hy2 > hy1:
                    roi = frame[hy1:hy2, hx1:hx2]
                    try:
                        blurred_roi = cv2.GaussianBlur(roi, (51, 51), 30)
                        frame[hy1:hy2, hx1:hx2] = blurred_roi
                    except Exception:
                        pass
        
            color = (0, 255, 100)
            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), color, 2)
            if show_confidence:
                label = f"#{det.track_id} {det.confidence:.2f}" if det.track_id >= 0 else f"{det.confidence:.2f}"
                cv2.putText(frame, label, (det.x1, det.y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame
