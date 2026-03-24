"""
Event Logger — timestamped log of every metric, alert, and incident.
Writes to SQLite and JSON flat files.
"""

import sqlite3
import json
import time
import os
import datetime
from dataclasses import dataclass, field, asdict
from collections import deque
from typing import List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import LOG_DIR, DB_PATH


@dataclass
class LogEntry:
    timestamp: float
    event_type: str       # METRIC | ALERT | ZONE_VIOLATION | BEHAVIOR | LOST_CHILD | SYSTEM
    level: str
    message: str
    data: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "time_str": datetime.datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S"),
            "event_type": self.event_type,
            "level": self.level,
            "message": self.message,
            "data": self.data
        }


class EventLogger:
    def __init__(self, session_id: Optional[str] = None):
        if session_id is None:
            session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_id
        os.makedirs(LOG_DIR, exist_ok=True)
        self.log_path = os.path.join(LOG_DIR, f"session_{session_id}.jsonl")
        self.memory: deque = deque(maxlen=1000)
        self._init_db()
        self._metric_buffer: List[dict] = []
        self._last_metric_flush = time.time()

    def _init_db(self):
        try:
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp REAL,
                    event_type TEXT,
                    level TEXT,
                    message TEXT,
                    data TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp REAL,
                    count INTEGER,
                    density REAL,
                    avg_speed REAL,
                    risk_score REAL,
                    alert_level TEXT
                )
            """)
            self.conn.commit()
        except Exception as e:
            print(f"[Logger] DB init error: {e}")
            self.conn = None

    def log(self, event_type: str, level: str, message: str, data: dict = None):
        entry = LogEntry(
            timestamp=time.time(),
            event_type=event_type,
            level=level,
            message=message,
            data=data or {}
        )
        self.memory.appendleft(entry)
        # Write to JSONL file
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception:
            pass
        # Write to DB
        if self.conn:
            try:
                self.conn.execute(
                    "INSERT INTO events (session_id,timestamp,event_type,level,message,data) VALUES (?,?,?,?,?,?)",
                    (self.session_id, entry.timestamp, event_type, level, message, json.dumps(data or {}))
                )
                self.conn.commit()
            except Exception as e:
                print(f"[Logger] DB write error: {e}")

    def log_metric(self, count: int, density: float, avg_speed: float,
                   risk_score: float, alert_level: str):
        now = time.time()
        self._metric_buffer.append({
            "ts": now, "count": count, "density": density,
            "avg_speed": avg_speed, "risk_score": risk_score, "alert_level": alert_level
        })
        if now - self._last_metric_flush > 5:
            self._flush_metrics()
            self._last_metric_flush = now

    def _flush_metrics(self):
        if not self.conn or not self._metric_buffer:
            return
        try:
            self.conn.executemany(
                "INSERT INTO metrics (session_id,timestamp,count,density,avg_speed,risk_score,alert_level) VALUES (?,?,?,?,?,?,?)",
                [(self.session_id, m["ts"], m["count"], m["density"],
                  m["avg_speed"], m["risk_score"], m["alert_level"])
                 for m in self._metric_buffer]
            )
            self.conn.commit()
            self._metric_buffer.clear()
        except Exception as e:
            print(f"[Logger] Metric flush error: {e}")

    def get_recent(self, n: int = 30) -> List[dict]:
        return [e.to_dict() for e in list(self.memory)[:n]]

    def generate_incident_timeline(self, session_name: str = "") -> str:
        """Generate a plain-text incident timeline from memory."""
        events = [e for e in self.memory
                  if e.level in ("WARNING", "DANGER", "CRITICAL")]
        events.sort(key=lambda x: x.timestamp)
        lines = []
        lines.append("=" * 60)
        lines.append(f"INCIDENT REPORT — Session: {self.session_id}")
        if session_name:
            lines.append(f"Venue: {session_name}")
        lines.append("=" * 60)
        lines.append("INCIDENT TIMELINE")
        lines.append("─" * 60)
        if not events:
            lines.append("  No incidents recorded this session.")
        for e in events:
            ts = datetime.datetime.fromtimestamp(e.timestamp).strftime("%H:%M:%S")
            lines.append(f"  {ts}   [{e.level}]  {e.message}")
            if e.data:
                for k, v in e.data.items():
                    lines.append(f"             {k}: {v}")
        lines.append("─" * 60)
        lines.append(f"Total events logged: {len(self.memory)}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def export_csv(self) -> str:
        """Export metric history to CSV. Returns file path."""
        import csv
        if not self.conn:
            return ""
        out_path = os.path.join(LOG_DIR, f"metrics_{self.session_id}.csv")
        try:
            rows = self.conn.execute(
                "SELECT timestamp,count,density,avg_speed,risk_score,alert_level FROM metrics WHERE session_id=?",
                (self.session_id,)
            ).fetchall()
            with open(out_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "count", "density", "avg_speed", "risk_score", "alert_level"])
                w.writerows(rows)
            return out_path
        except Exception as e:
            print(f"[Logger] CSV export error: {e}")
            return ""

    def close(self):
        self._flush_metrics()
        if self.conn:
            self.conn.close()
