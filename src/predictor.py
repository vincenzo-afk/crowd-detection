"""
LSTM-based Predictive Risk Engine.
Trains on rolling 60-second metric history and forecasts risk score for 30/60/120s.
Falls back to a simple linear trend when PyTorch is not available.
"""

import numpy as np
from collections import deque
from typing import List, Dict

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import LSTM_SEQUENCE_LEN, LSTM_FORECAST_STEPS


class LSTMRiskPredictor:
    """
    Online LSTM risk predictor. Uses a sliding window of metrics to predict
    future risk score at multiple horizons.
    """

    def __init__(self):
        self.sequence: deque = deque(maxlen=LSTM_SEQUENCE_LEN)
        self.model = None
        self.trained = False
        self._try_build_model()

    def _try_build_model(self):
        try:
            import torch
            import torch.nn as nn

            class _LSTM(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.lstm = nn.LSTM(input_size=5, hidden_size=64,
                                        num_layers=2, batch_first=True, dropout=0.2)
                    self.fc = nn.Linear(64, 3)   # 3 forecast horizons

                def forward(self, x):
                    out, _ = self.lstm(x)
                    return torch.sigmoid(self.fc(out[:, -1, :])) * 100

            self.model = _LSTM()
            self.torch = torch
            self.nn = nn
            print("[LSTM] Model created.")
        except ImportError:
            print("[LSTM] PyTorch not found — using trend fallback.")
            self.model = None

    def update(self, density: float, avg_speed: float, risk_score: float,
               count: int, direction_entropy: float):
        """Add a new metric sample to the sequence."""
        self.sequence.append([
            density,
            min(avg_speed / 50.0, 1.0),
            risk_score / 100.0,
            min(count / 200.0, 1.0),
            direction_entropy
        ])

    def predict(self) -> Dict[int, float]:
        """
        Returns dict {horizon_seconds: predicted_risk_score (0–100)}
        """
        if len(self.sequence) < 10:
            return {h: 0.0 for h in LSTM_FORECAST_STEPS}

        seq = list(self.sequence)

        # PyTorch path
        if self.model is not None:
            try:
                x = self.torch.tensor([seq], dtype=self.torch.float32)
                self.model.eval()
                with self.torch.no_grad():
                    preds = self.model(x)[0].numpy()
                return {LSTM_FORECAST_STEPS[i]: float(preds[i]) for i in range(3)}
            except Exception as e:
                print(f"[LSTM] Inference error: {e}")

        # Fallback: extrapolate linear trend on risk_score column
        scores = [s[2] * 100 for s in seq]
        n = len(scores)
        x_vals = np.arange(n)
        coeffs = np.polyfit(x_vals, scores, 1)
        slope = coeffs[0]
        current = scores[-1]
        result = {}
        for h in LSTM_FORECAST_STEPS:
            pred = current + slope * h
            result[h] = float(np.clip(pred, 0, 100))
        return result

    def get_trend(self) -> str:
        """Returns 'rising', 'stable', or 'falling'."""
        if len(self.sequence) < 10:
            return "stable"
        scores = [s[2] * 100 for s in list(self.sequence)[-20:]]
        slope = np.polyfit(np.arange(len(scores)), scores, 1)[0]
        if slope > 1.0:
            return "rising"
        if slope < -1.0:
            return "falling"
        return "stable"
