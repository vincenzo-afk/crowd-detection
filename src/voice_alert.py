"""
Voice Alert System — TTS announcements for crowd safety events.
Uses pyttsx3 (offline) with fallback to print-only mode.
Supports English and multilingual alert scripts.
All speech runs in a non-blocking background thread.
"""

import threading
import time
import queue
from typing import Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import ALERT_WARNING, ALERT_DANGER, ALERT_CRITICAL


# ── Alert scripts per level ──────────────────────────────────────────────────

ALERT_SCRIPTS = {
    ALERT_WARNING: [
        "Attention please. Crowd density is increasing. Please maintain safe distances.",
        "Warning: Crowd levels are rising. Security personnel, please monitor the area.",
    ],
    ALERT_DANGER: [
        "Danger alert. Crowd congestion detected. Please move away from crowded areas immediately.",
        "Crowd pressure is critical. Security team, please respond to the flagged zone.",
    ],
    ALERT_CRITICAL: [
        "Emergency. Stampede risk detected. Please remain calm and move to the nearest exit quickly.",
        "Critical crowd compression. All security personnel respond immediately. Emergency protocol activated.",
    ],
    "LOST_CHILD": [
        "Attention security. A possible lost child has been detected. Please check the flagged zone immediately.",
    ],
}


class VoiceAlertSystem:
    """
    Non-blocking TTS voice alert system.
    Uses a background thread and a speech queue with cooldown per level.
    """

    def __init__(self, cooldown_per_level: float = 30.0):
        self.cooldown = cooldown_per_level
        self._last_spoken: dict = {}
        self._queue: queue.Queue = queue.Queue(maxsize=8)
        self._engine = None
        self._running = True
        self._script_index: dict = {k: 0 for k in ALERT_SCRIPTS}
        self._try_init_engine()
        self._worker = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker.start()

    def _try_init_engine(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 165)
            self._engine.setProperty("volume", 1.0)
            print("[Voice] TTS engine initialised.")
        except Exception as e:
            print(f"[Voice] TTS unavailable ({e}). Simulating speech output.")
            self._engine = None

    def _get_next_script(self, level: str) -> str:
        scripts = ALERT_SCRIPTS.get(level, [f"{level} alert detected."])
        idx = self._script_index.get(level, 0) % len(scripts)
        self._script_index[level] = idx + 1
        return scripts[idx]

    def speak(self, level: str, custom_text: Optional[str] = None):
        """Queue a speech request if cooldown has passed."""
        now = time.time()
        last = self._last_spoken.get(level, 0)
        if now - last < self.cooldown:
            return
        self._last_spoken[level] = now
        text = custom_text or self._get_next_script(level)
        try:
            self._queue.put_nowait(text)
        except queue.Full:
            pass

    def _speech_worker(self):
        while self._running:
            try:
                text = self._queue.get(timeout=1.0)
                print(f"[Voice] 🔊 {text}")
                if self._engine:
                    try:
                        self._engine.say(text)
                        self._engine.runAndWait()
                    except Exception as e:
                        print(f"[Voice] TTS error: {e}")
            except queue.Empty:
                continue

    def stop(self):
        self._running = False
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
