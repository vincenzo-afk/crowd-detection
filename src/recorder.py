"""
Video incident recorder.
Maintains a rolling buffer of frames and saves video clips
when a Danger or Critical alert triggers.
"""

import cv2
import collections
import threading
import time
import os

from config.settings import RECORDING_DIR

class IncidentRecorder:
    def __init__(self, fps=30, pre_seconds=30, post_seconds=120):
        self.fps = max(1, fps)
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.buffer = collections.deque(maxlen=self.fps * self.pre_seconds)
        self.recording = False
        self.frames_to_record = 0
        self.frames_recorded = 0
        self._writer = None
        self._filename = None
        os.makedirs(RECORDING_DIR, exist_ok=True)
        
    def update(self, frame):
        """Append frame to buffer. Handle active recording."""
        self.buffer.append(frame)
        if self.recording:
            if self._writer and self.frames_recorded < self.frames_to_record:
                self._writer.write(frame)
                self.frames_recorded += 1
            else:
                self._stop_recording()
                
    def trigger(self, alert_level, metrics=None):
        """Begin saving to disk when trigger occurs."""
        if self.recording:
            # Extend recording if already running
            self.frames_to_record = self.fps * self.post_seconds
            self.frames_recorded = 0
            return
            
        if not self.buffer:
            return
            
        self.recording = True
        self.frames_to_record = self.fps * self.post_seconds
        self.frames_recorded = 0
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self._filename = os.path.join(RECORDING_DIR, f"incident_{timestamp}_{alert_level}.mp4")
        
        h, w = self.buffer[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._writer = cv2.VideoWriter(self._filename, fourcc, self.fps, (w, h))
        
        # Dump pre-buffer to file immediately
        for f in self.buffer:
            self._writer.write(f)
            
        print(f"[Recorder] Triggered {alert_level}. Dumping pre-clip and recording to {self._filename}...")
        
    def _stop_recording(self):
        self.recording = False
        if self._writer:
            self._writer.release()
            self._writer = None
            print(f"[Recorder] Recording saved: {self._filename}")
            
    def close(self):
        self._stop_recording()
