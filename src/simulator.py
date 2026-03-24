"""
Crowd Simulation Engine — generates synthetic detections for demo / testing.
Gradually increases density, then triggers a stampede pattern.
"""

import numpy as np
import random
import time
import math
from typing import List

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SIM_INITIAL_PEOPLE, SIM_MAX_PEOPLE, FRAME_WIDTH, FRAME_HEIGHT
from src.detector import Detection


class SimPerson:
    def __init__(self, pid: int, W: int, H: int):
        self.id = pid
        self.x = random.uniform(W * 0.1, W * 0.9)
        self.y = random.uniform(H * 0.2, H * 0.9)
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-1.5, 1.5)
        self.w = random.randint(40, 60)
        self.h = random.randint(80, 110)
        self.W = W; self.H = H

    def step(self, mode: str = "normal", target_x: float = None, target_y: float = None):
        if mode == "panic":
            # Rush outward
            cx, cy = self.W // 2, self.H // 2
            dx = self.x - cx; dy = self.y - cy
            mag = math.hypot(dx, dy) or 1
            self.vx = (dx / mag) * random.uniform(8, 15)
            self.vy = (dy / mag) * random.uniform(8, 15)
        elif mode == "surge" and target_x is not None:
            dx = target_x - self.x; dy = (target_y or self.H * 0.5) - self.y
            mag = math.hypot(dx, dy) or 1
            self.vx = (dx / mag) * random.uniform(5, 10)
            self.vy = (dy / mag) * random.uniform(5, 10)
        else:
            self.vx += random.uniform(-0.3, 0.3)
            self.vy += random.uniform(-0.3, 0.3)
            self.vx = max(-2, min(2, self.vx))
            self.vy = max(-2, min(2, self.vy))

        self.x = max(self.w // 2, min(self.W - self.w // 2, self.x + self.vx))
        self.y = max(self.h // 2, min(self.H - self.h // 2, self.y + self.vy))

    def to_detection(self) -> Detection:
        x1 = int(self.x - self.w // 2)
        y1 = int(self.y - self.h // 2)
        x2 = int(self.x + self.w // 2)
        y2 = int(self.y + self.h // 2)
        return Detection(x1, y1, x2, y2, confidence=0.92, track_id=self.id)


class CrowdSimulator:
    MODES = ["normal", "building", "dense", "panic", "surge"]

    def __init__(self, W: int = FRAME_WIDTH, H: int = FRAME_HEIGHT):
        self.W = W; self.H = H
        self.people: List[SimPerson] = []
        self.mode = "normal"
        self.mode_start = time.time()
        self._next_id = 1
        self._frame = 0
        self._spawn_initial()

    def _spawn_initial(self):
        for _ in range(SIM_INITIAL_PEOPLE):
            self._spawn_one()

    def _spawn_one(self):
        p = SimPerson(self._next_id, self.W, self.H)
        self._next_id += 1
        self.people.append(p)

    def set_mode(self, mode: str):
        if mode in self.MODES:
            self.mode = mode
            self.mode_start = time.time()

    def step(self) -> List[Detection]:
        self._frame += 1
        elapsed = time.time() - self.mode_start

        # Spawn more people in building/dense mode
        if self.mode == "building" and len(self.people) < SIM_MAX_PEOPLE / 2:
            if self._frame % 30 == 0:
                self._spawn_one()
        elif self.mode == "dense" and len(self.people) < SIM_MAX_PEOPLE:
            if self._frame % 10 == 0:
                self._spawn_one()

        for p in self.people:
            p.step(self.mode, target_x=self.W * 0.5, target_y=self.H * 0.8)

        return [p.to_detection() for p in self.people]

    def render_blank_frame(self, frame=None):
        import numpy as np
        if frame is None:
            frame = np.zeros((self.H, self.W, 3), dtype=np.uint8)
            # Gradient background
            for i in range(self.H):
                c = int(15 + (i / self.H) * 20)
                frame[i, :] = [c, c, c]
        return frame
