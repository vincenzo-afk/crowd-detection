"""
FastAPI-based web dashboard backend.
Serves the HTML dashboard, video stream via MJPEG, and a WebSocket for live data.
"""

import asyncio
import base64
import json
import time
import os
import threading
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import API_HOST, API_PORT, RECORDING_DIR

# Shared state object injected from main pipeline
_state: dict = {
    "frame": None,
    "metrics": {},
    "alert_feed": [],
    "alert_level": "SAFE",
    "risk_score": 0.0,
    "predictions": {},
    "running": False,
    "sim_mode": False,
}

app = FastAPI(title="Crowd Safety Dashboard", version="1.0")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "web", "templates")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

app.mount("/recordings", StaticFiles(directory=RECORDING_DIR), name="recordings")


def get_state() -> dict:
    return _state


def update_state(**kwargs):
    _state.update(kwargs)


# ── MJPEG stream ────────────────────────────────────────────────────────────

def _frame_generator():
    while True:
        frame = _state.get("frame")
        if frame is not None:
            try:
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
            except Exception:
                pass
        time.sleep(0.033)


@app.get("/stream")
def video_stream():
    return StreamingResponse(
        _frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ── WebSocket live data ──────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()   # keep alive pings
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def _broadcast_loop():
    while True:
        await asyncio.sleep(0.5)
        try:
            data = {
                "metrics": _state.get("metrics", {}),
                "alert_level": _state.get("alert_level", "SAFE"),
                "risk_score": _state.get("risk_score", 0),
                "predictions": _state.get("predictions", {}),
                "alert_feed": _state.get("alert_feed", [])[:10],
                "running": _state.get("running", False),
            }
            await manager.broadcast(data)
        except Exception:
            pass


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status():
    m = _state.get("metrics", {})
    return JSONResponse({
        "alert_level": _state.get("alert_level", "SAFE"),
        "risk_score": _state.get("risk_score", 0),
        "count": m.get("count", 0),
        "density": m.get("density", 0),
        "running": _state.get("running", False),
        "predictions": _state.get("predictions", {}),
    })


@app.get("/api/alerts")
def api_alerts():
    return JSONResponse({"alerts": _state.get("alert_feed", [])})


@app.post("/api/control/{action}")
async def api_control(action: str):
    if action == "start":
        _state["running"] = True
    elif action == "stop":
        _state["running"] = False
    elif action == "sim_normal":
        _state["sim_cmd"] = "normal"
    elif action == "sim_building":
        _state["sim_cmd"] = "building"
    elif action == "sim_dense":
        _state["sim_cmd"] = "dense"
    elif action == "sim_panic":
        _state["sim_cmd"] = "panic"
    return JSONResponse({"status": "ok", "action": action})


@app.get("/api/timeline")
def api_timeline():
    timeline = _state.get("timeline", "")
    if not timeline:
        timeline = "No recent incident recorded."
    return JSONResponse({"timeline": timeline})

@app.get("/api/recordings")
def api_list_recordings():
    """Returns a list of all recorded mp4 incident clips."""
    recs = []
    if os.path.exists(RECORDING_DIR):
        for f in reversed(sorted(os.listdir(RECORDING_DIR))):
            if f.endswith(".mp4"):
                recs.append(f)
    return JSONResponse({"recordings": recs})

@app.post("/api/camera/{cam_id}")
async def api_switch_camera(cam_id: str):
    """Multi-camera switching endpoint API."""
    _state["current_camera"] = cam_id
    print(f"[Dashboard] Switched to Camera: {cam_id}")
    return JSONResponse({"status": "ok", "camera": cam_id})


@app.get("/")
def index(request: Request):
    """Main dashboard interface."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/mobile")
def mobile_index(request: Request):
    """Mobile Command Center interface."""
    return templates.TemplateResponse("mobile.html", {"request": request})


@app.on_event("startup")
async def startup():
    asyncio.create_task(_broadcast_loop())


def start_server(host: str = API_HOST, port: int = API_PORT):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")
