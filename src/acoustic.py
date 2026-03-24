"""
Acoustic Panic Detection Module.
Runs an audio analysis pipeline in a background thread.
Detects screaming, sudden crowd noise spikes, and panic-level sound.
Uses PyAudio + numpy FFT. Falls back to simulation if PyAudio unavailable.
"""

import threading
import time
import math
import queue
from collections import deque
from typing import Optional

import numpy as np

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
PANIC_DB_THRESHOLD = 75.0      # dB SPL equivalent — sustained loud noise
SCREAM_FREQ_LOW = 1000         # Hz  — scream / shout frequency band
SCREAM_FREQ_HIGH = 4000        # Hz
BASELINE_WINDOW = 60           # seconds of baseline


class AcousticDetector:
    """
    Listens to the default microphone input and computes:
      - Rolling dB level
      - Energy in scream/shout frequency band
      - Panic score (0–100)
    Raises a flag when a panic-level audio event is detected.
    """

    def __init__(self):
        self.panic_score: float = 0.0
        self.db_level: float = 0.0
        self.is_panic: bool = False
        self._db_history: deque = deque(maxlen=SAMPLE_RATE // CHUNK_SIZE * BASELINE_WINDOW)
        self._running = False
        self._pyaudio = None
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        self._simulated = False
        self._sim_t = 0.0

    def start(self):
        """Start the audio capture thread."""
        self._running = True
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            print("[Acoustic] Microphone capture active.")
            self._simulated = False
        except Exception as e:
            print(f"[Acoustic] PyAudio unavailable ({e}). Running in simulated mode.")
            self._simulated = True

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass

    def _loop(self):
        while self._running:
            if self._simulated:
                self._sim_step()
            else:
                self._real_step()
            time.sleep(0.05)

    def _real_step(self):
        try:
            data = self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            self._process(samples)
        except Exception:
            time.sleep(0.1)

    def _sim_step(self):
        """Simulated audio — slowly oscillates with occasional spikes."""
        self._sim_t += 0.05
        base = 45.0 + 10.0 * math.sin(self._sim_t * 0.2)
        # Random noise spikes
        spike = 40.0 * max(0, math.sin(self._sim_t * 0.07) ** 8)
        db = base + spike + np.random.normal(0, 2)
        self.db_level = float(np.clip(db, 30, 100))
        self._compute_panic_score_from_db(self.db_level)

    def _process(self, samples: np.ndarray):
        """Compute RMS dB and frequency band energy."""
        rms = math.sqrt(max(float(np.mean(samples ** 2)), 1e-10))
        db = 20 * math.log10(rms / 32768.0) + 96  # normalised to ~SPL
        self.db_level = float(np.clip(db, 0, 120))

        # FFT for scream band energy
        fft = np.abs(np.fft.rfft(samples, n=CHUNK_SIZE))
        freqs = np.fft.rfftfreq(CHUNK_SIZE, d=1.0 / SAMPLE_RATE)
        band_mask = (freqs >= SCREAM_FREQ_LOW) & (freqs <= SCREAM_FREQ_HIGH)
        total_energy = np.sum(fft ** 2) + 1e-10
        scream_energy = float(np.sum(fft[band_mask] ** 2) / total_energy)

        self._compute_panic_score(self.db_level, scream_energy)

    def _compute_panic_score_from_db(self, db: float):
        self._db_history.append(db)
        baseline = float(np.mean(self._db_history)) if len(self._db_history) > 10 else 50.0
        excess = max(0.0, db - baseline - 10.0)
        self.panic_score = float(np.clip(excess * 3.0, 0, 100))
        self.is_panic = self.panic_score > 60.0

    def _compute_panic_score(self, db: float, scream_ratio: float):
        self._db_history.append(db)
        baseline = float(np.mean(self._db_history)) if len(self._db_history) > 10 else 50.0
        db_excess = max(0.0, db - baseline - 8.0)
        scream_contribution = scream_ratio * 40.0
        self.panic_score = float(np.clip(db_excess * 2.5 + scream_contribution, 0, 100))
        self.is_panic = self.panic_score > 60.0

    def get_status(self) -> dict:
        return {
            "db_level": round(self.db_level, 1),
            "panic_score": round(self.panic_score, 1),
            "is_panic": self.is_panic,
            "simulated": self._simulated,
        }
