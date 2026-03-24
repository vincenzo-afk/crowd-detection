# Intelligent Crowd Safety & Stampede Prevention System

An AI-powered real-time crowd monitoring system that detects people, tracks movement, measures density, predicts dangerous situations, and triggers alerts — all before a stampede or crowd accident can happen.

Built for real-world deployment at railway stations, temples, stadiums, malls, concerts, and any high-footfall public space.

---

## What This System Does

Most CCTV systems just record. This system **thinks**.

It watches a crowd in real time, understands what is happening, predicts what is about to happen, and warns the right people with enough time to act. The goal is simple — prevent crowd accidents before they occur, not document them after.

---

## System Pipeline

```
Video Input → Person Detection → Tracking → Density Analysis
           → Movement Analysis → Risk Prediction → Alert → Dashboard + Logs
```

Every frame goes through this pipeline continuously, producing live risk scores, alerts, and visualizations.

---

## Input Sources Supported

- Webcam (laptop or USB camera)
- CCTV / IP camera feed (RTSP stream)
- Pre-recorded video file (MP4, AVI, etc.)
- Multiple cameras simultaneously
- Drone video feed (aerial crowd monitoring)

---

## Feature List

---

### People Detection

The system uses YOLOv8, a state-of-the-art AI detection model, to find every person in the camera frame in real time.

- Detects people frame by frame at 30+ FPS
- Draws a bounding box around each detected person
- Shows a confidence score for each detection
- Works in low-light and crowded conditions
- Tracks detection accuracy as a running metric

---

### Person Tracking

Once detected, every person gets a unique ID and is followed across frames — even if they leave the frame briefly and come back.

- Each person assigned a unique numeric ID
- ID persists across frames even through partial occlusion
- Stores movement history (trajectory) of each tracked person
- Re-identifies people who briefly disappear from frame
- Handles large crowds with many simultaneous tracks

---

### Crowd Counting

Accurate headcount at all times, broken into several modes.

**Live Count**
- Total number of people visible right now
- Rolling average count to reduce noise from flickering detections
- Peak count recorded with timestamp

**Entry and Exit Counting**
- A virtual line can be drawn across any entry or exit point
- System counts how many people cross in each direction
- Calculates current occupancy: people who entered minus people who left

**Capacity Monitoring**
- Set a maximum safe capacity for the venue
- System shows occupancy as a percentage in real time
- Triggers a warning when capacity threshold is approached or exceeded

---

### Crowd Density Analysis

Density goes beyond just counting — it measures how tightly packed people are and where the dangerous zones are forming.

**Global Density**
- Calculates overall density across the full frame
- Compares to safe and danger thresholds
- Triggers alerts when density crosses configured limits

**Zone-Based Density**
- Frame is divided into a grid of zones (configurable)
- Each zone gets its own density score and risk label
- Lets operators see exactly which part of the crowd is dangerous

**Dynamic Density**
- Tracks how density is changing over time (rising, stable, falling)
- Detects sudden density spikes
- Moving average smooths out noise for cleaner trend data

---

### Heatmap Visualization

Heatmaps give operators an instant visual understanding of where crowd pressure is building.

- **Density Heatmap** — overlaid on the live feed, color-coded from green (safe) to red (critical)
- **Motion Heatmap** — shows where movement is most frequent
- **Historical Heatmap** — accumulates data over the session to show persistent hotspots

---

### Movement Analysis

The system doesn't just count people — it understands how they are moving.

**Speed Analysis**
- Calculates the speed of each individual (converted to real-world units when camera is calibrated)
- Tracks average crowd speed
- Detects sudden speed spikes — a key pre-stampede indicator

**Direction Analysis**
- Detects the movement direction of each person
- Measures how consistent the crowd's direction is
- Detects when a large portion of the crowd suddenly reverses or surges in one direction

**Flow Analysis**
- Visualizes crowd flow as directional arrows on the live feed
- Detects flow congestion — areas where movement is blocked or compressed
- Identifies bottlenecks forming at exits or narrow passages

---

### Stampede Detection

This is the core safety feature. The system watches for the specific patterns that appear before a stampede.

- **Sudden speed increase** — multiple people accelerating sharply at the same time
- **Crowd compression** — people getting too close together, inter-person distance dropping below the danger threshold
- **Direction surge** — a large portion of the crowd suddenly moving in the same direction
- **Escape pattern** — mass movement away from a central point (explosion pattern)
- **Pressure wave detection** — detects compression waves spreading through the crowd

When these patterns are detected together, the system escalates to a danger or critical alert immediately.

---

### Predictive Risk Engine

The system doesn't just react — it predicts.

An LSTM (Long Short-Term Memory) neural network is trained on the last 60 seconds of crowd metrics and outputs a risk forecast for the next 30, 60, and 120 seconds.

- Predicts density growth before it becomes dangerous
- Forecasts crowd speed trends
- Outputs a risk score (0–100%) shown as a live gauge on the dashboard
- Gives operators 1–2 minutes of genuine advance warning before visible danger appears
- Forecast horizon is configurable

---

### Behavior Detection

The system also monitors individual-level behaviors that indicate danger.

| Behavior | How It's Detected |
|---|---|
| Person falling | Sudden vertical drop, bounding box shifts to horizontal |
| Running | Speed far above the crowd average |
| Loitering | Person remains stationary for longer than a set time |
| Erratic movement | Irregular path, rapid direction changes out of sync with the crowd |

---

### Group and Cluster Analysis

Dangerous crowd situations often start with the formation of dense clusters.

- Detects clusters of people forming using spatial proximity analysis
- Calculates the size of each identified cluster
- Flags clusters that are too tight (high compression risk)
- Detects when two clusters rapidly merge — a danger signal
- Tracks cluster movement speed and direction as a unit

---

### Social Distance Monitoring

Useful for regulated events or health scenarios.

- Measures the distance between every pair of people in the frame
- Flags pairs that are closer than the configured minimum safe distance
- Counts total violations per session
- Draws colored lines between violating pairs on the live feed

---

### Restricted Zone Enforcement

Define areas that should remain off-limits and monitor them automatically.

- Draw polygon zones on the frame to mark restricted areas
- System detects any person entering a restricted zone in real time
- Logs each violation with timestamp and person ID
- Triggers an alert immediately on unauthorized entry

---

### Zone Management

Full control over how the space is divided for monitoring.

- Create zones manually using coordinates or a graphical drawing tool
- Edit, resize, and rename zones at any time
- Save and load zone configurations from files
- Different zones can have different alert thresholds

---

### Alert System

A four-level alert system that escalates based on how dangerous the situation is.

| Level | Color | What Triggers It |
|---|---|---|
| Safe | Green | All metrics normal |
| Warning | Yellow | One metric approaching danger |
| Danger | Orange | Multiple metrics in danger zone |
| Critical | Red | Stampede signature detected |

**Visual Alerts**
- Screen overlay changes color based on alert level
- Warning banners appear with a plain-language description of what is happening
- Per-zone risk indicators on the live map

**Audio Alerts**
- Escalating alert tones
- Siren sound at Critical level

**Smart Alert Logic**
- Multiple conditions must align before an alert fires — prevents false positives from a single noisy metric
- Cooldown period between alerts to prevent notification flooding
- Priority queue ensures the most serious alert always gets through first

---

### Voice Alert System

Automated spoken announcements for on-site personnel and crowd management.

- Text-to-speech engine announces alert conditions in spoken language
- Different announcement scripts per alert level
- Supports English and regional languages (Hindi, Tamil, etc.)
- Can be routed to the venue's PA system via audio output

---

### Data Logging

Everything is recorded.

- Timestamped log entry for every alert, detection event, and zone violation
- Frame-by-frame crowd count, density, and speed history stored to file
- System performance logs: FPS, CPU/GPU usage, errors
- All logs organized by session date and time

---

### Analytics

Both real-time and historical analytics are available.

- Live statistics panel on the dashboard showing all key metrics at once
- Historical graphs of density, speed, and count over the session
- Peak analysis: when did the highest density occur, at what time, in which zone
- Average and maximum metrics per session for reporting

---

### Live Operations Dashboard

A unified screen for crowd managers to see everything at once.

- Annotated live video feed with bounding boxes, heatmap overlay, and zone markings
- Statistics panel updated in real time
- Color-coded zone map showing risk level per zone
- Scrolling alert feed showing recent events
- System health panel: uptime, FPS, CPU, GPU load
- Control buttons: Start, Stop, Reset system

---

### Multi-Camera Support

For large venues that require coverage from multiple angles.

- Multiple camera feeds processed simultaneously
- Camera switching interface for operators
- Each camera maintains its own statistics and alerts independently
- Global crowd count aggregated across all cameras
- Feeds are time-synchronized

---

### Drone Feed Support

For outdoor events, religious gatherings, and large open areas where fixed cameras can't cover everything.

- Video from drone feeds is processed through the same detection and analysis pipeline
- Enables aerial crowd density mapping
- Wide-area monitoring not possible with fixed CCTV

---

### Incident Recording and Replay

Every dangerous event is captured and preserved.

- Continuous background recording of the processed video output
- When a Danger or Critical alert fires, the system automatically saves a clip from 30 seconds before to 2 minutes after the alert
- Replay mode lets operators review the incident with all overlays still visible
- Each incident clip is saved with metadata: time, zone, alert level, crowd metrics at that moment

---

### Simulation and Test Mode

For demonstrations, testing, and calibrating thresholds without needing a real crowd.

- Simulated crowd agents can be injected into the pipeline
- Gradually increase simulated density to test warning thresholds
- Trigger a simulated stampede pattern to test the full alert chain
- Perfect for expo demos, presentations, and system validation before deployment

---

### Privacy and Security

Responsible surveillance with built-in privacy protections.

- Automatic face blurring on all stored footage — no faces are saved
- No personally identifiable information is retained
- Encrypted local storage for logs and recordings
- Login authentication required before accessing the dashboard
- Admin and operator roles with separate permission levels

---

### Performance Optimization

The system is designed to run well even on modest hardware.

- Adaptive frame rate based on available compute power
- Frame skipping under high load without losing tracking continuity
- GPU acceleration via CUDA when an NVIDIA GPU is available
- Separate processing threads for capture, analysis, and rendering — nothing blocks anything else
- Live CPU and GPU usage displayed on the dashboard

---

### System Health Monitoring

The system monitors itself to ensure uninterrupted operation.

- Uptime counter displayed on dashboard
- Automatic detection of processing failures
- Camera feed loss detection with automatic reconnect attempts
- Watchdog timer restarts crashed threads automatically
- System health status visible at all times

---

### Notification Pipeline

When alerts fire, the right people are notified immediately through multiple channels.

- **SMS** — sends a message to configured phone numbers on Danger or Critical alert
- **Email** — sends an incident summary with a metrics snapshot
- **Push Notification** — sends a mobile push notification via Firebase
- **Webhook** — sends a POST request to any configured external system or command center

---

### Reports and Export

Structured documentation at the end of every session.

- Daily session report generated automatically
- Full metrics history exported to CSV for data analysis
- Formatted PDF incident report with charts and timeline
- Incident summary listing all alert events with timestamps and context

---

### Advanced AI Modules

- **Behavior Classification** — a trained classifier labels movement as normal or panic-pattern
- **Anomaly Detection** — detects crowd behaviors that don't match any known safe pattern
- **Model Retraining Pipeline** — labeled data from real sessions can be used to improve the detection and classification models over time

---

### Lost Child and Missing Person Detection

One of the most human and emotionally powerful features in the system. Extremely relevant for malls, temples, religious festivals, and any event with families.

**What It Detects**

The system continuously scans the crowd for signs of a child being alone or separated from their group.

- **Isolated small figure** — detects a person significantly smaller in bounding box size than surrounding adults, indicating a child, who has no adult within a configurable proximity radius
- **Stationary child** — a small figure that has remained in the same spot for an extended period while the crowd around them is moving, which is a strong signal of a lost or distressed child
- **Child separated from group** — if a small figure was previously close to a cluster of adults and that cluster has moved away while the child stayed behind, the system flags this separation event
- **Child moving erratically** — small figure moving in irregular directions, inconsistent with the general crowd flow, suggesting confusion or distress

**How It Works**

YOLOv8 estimates relative body size from bounding box height. Children have a significantly smaller bounding box height compared to adults in the same frame depth. The tracker maintains each person's size classification and monitors proximity to other adults over time. When a small figure is alone for more than the configured duration, an alert fires.

**Optional: Face Recognition Match**

If a photo of a missing child is submitted to the system (by a parent or security personnel), the system activates a face recognition scan across all camera feeds and flags the moment a match is detected, along with the camera ID and zone location.

**Alert Behavior**

- Dashboard shows a highlighted bounding box in a distinct color (orange) around the flagged child
- Alert message: "Possible lost child detected — Zone B — Camera 2 — stationary for 3 minutes"
- SMS and push notification sent to security personnel immediately
- Zone is flagged on the dashboard map so the nearest guard can respond

**Real-World Value**

This feature directly addresses a life-safety and child-safety problem that occurs at every large public gathering. It has immediate emotional resonance with judges, venue operators, and the general public. No standard crowd monitoring system includes this. It is one of the strongest differentiators in the project.

---

### Incident Timeline Generator

After any dangerous event, the first thing investigators, venue managers, and legal teams need is a clear record of exactly what happened and in what sequence. This feature produces that automatically.

**What It Is**

The system maintains a live event log throughout every session. When a session ends or when a Critical alert is resolved, the system automatically compiles all logged events into a structured, human-readable incident timeline.

**Example Output**

```
INCIDENT REPORT — Session: 2024-03-15  Venue: Main Gate Area

INCIDENT TIMELINE
─────────────────────────────────────────────────────
12:01:05   Occupancy reached 80% of configured capacity
12:01:20   Zone C density crossed WARNING threshold (density: 71%)
12:01:28   Average crowd speed increased 1.8x above baseline
12:01:35   Speed surge detected — Zone C (2.4x baseline)
12:01:38   Direction entropy dropped — 68% of crowd moving north
12:01:42   Panic movement pattern confirmed
12:01:44   Crowd compression detected — Zone C (avg distance: 0.5m)
12:01:45   CRITICAL ALERT TRIGGERED — Stampede risk: 94%
12:01:45   SMS sent to: +91XXXXXXXXXX, +91XXXXXXXXXX
12:01:45   Voice announcement triggered: "Please move back, emergency"
12:01:52   Security acknowledged alert
12:02:10   Density in Zone C began decreasing
12:02:45   Risk score returned below danger threshold
12:02:45   Incident resolved — Duration: 1 minute 40 seconds

SUMMARY
Peak density: 84% — Zone C
Peak speed multiplier: 2.4x baseline
Total people affected: ~180
Incident duration: 100 seconds
Alert-to-response time: 7 seconds
─────────────────────────────────────────────────────
```

**What Gets Included**

- Every metric threshold breach with the exact value at the time
- Every alert fired, at what level, and which conditions triggered it
- Every notification sent and to whom
- Security personnel acknowledgements
- When and how the situation resolved
- Summary statistics: peak values, duration, people affected, response time

**Export Options**

- PDF report with the full timeline formatted for official documentation
- CSV export of the raw event log for data analysis
- JSON export for integration with external incident management systems

**Why This Matters**

Venues are legally liable for crowd safety incidents. An automatically generated, timestamped, detailed incident report is not just useful — it is essential for legal protection, insurance claims, investigation, and improving future safety procedures. This feature makes the system deployable in professional and institutional environments, not just academic demonstrations.

---

### Edge AI Mode — Offline Operation

This feature makes the system deployable in the real world, not just in a lab with reliable internet.

**The Problem It Solves**

Most AI systems require cloud connectivity for inference — sending video frames to a remote server and waiting for results. This is completely impractical for crowd safety. Network delays of even 1–2 seconds can mean the difference between a warning and a tragedy. Internet outages happen. At large outdoor events, mobile networks get congested. The system must work regardless.

**What Edge AI Mode Does**

All AI models — person detection, tracking, density estimation, behavior classification, and risk prediction — are optimized and bundled to run entirely on the local device. No internet connection is required for any part of the analysis pipeline.

- YOLOv8 model is exported to ONNX format and quantized (INT8) for fast CPU inference
- LSTM risk model runs locally using ONNX Runtime
- All alerts, logs, notifications (SMS via local SIM if configured), and dashboard updates happen on-device
- System boots into operational mode automatically — no manual setup required at deployment

**Performance on Different Hardware**

| Device | Mode | Expected FPS |
|---|---|---|
| Standard laptop (CPU only) | Lightweight YOLOv8n | 15–25 FPS |
| Laptop with NVIDIA GPU | Full pipeline | 30+ FPS |
| Jetson Nano / Orin | Edge-optimized ONNX | 20–30 FPS |
| Raspberry Pi 5 | Detection only mode | 8–12 FPS |

**What Still Works Offline**

- Full person detection and tracking
- All density, speed, and movement analysis
- Stampede detection and all alert levels
- Voice alerts and audio alerts
- Dashboard and all visualizations
- Incident recording and replay
- Incident timeline generation
- Data logging and local report generation

**What Requires Internet (Optional Features)**

- SMS and push notifications via cloud services (Twilio, Firebase) — can be replaced with local SIM modem
- Weather-aware risk adjustment — falls back to standard thresholds when offline
- LLM-generated incident reports — cached templates used as fallback

**Why Judges and Real Deployments Care About This**

A system that only works with reliable internet is a demo project. A system that works on a Jetson device bolted to a wall at a railway station, with no internet, in a power-fluctuating environment, for 12 hours straight — that is a real product. Edge AI mode is what separates a university project from something that could actually be deployed and save lives. It demonstrates engineering maturity, real-world thinking, and production-level design decisions.

---

## Additional Power Features

---

### Acoustic Panic Detection

A separate audio analysis pipeline runs in parallel with the video feed.

- Detects screaming, sudden loud crowd noise, and panic-level sound spikes using a trained audio classifier
- Audio and video risk scores are combined — when both flag danger at the same time, the system is far more confident in the alert
- Still works if the camera feed is obstructed or temporarily drops

---

### Graph Neural Network Crowd Flow Prediction

Instead of analyzing each person in isolation, the system builds a graph where every person is a node and their spatial closeness to others forms the edges. A Graph Neural Network runs on this structure.

- Models the crowd as a connected system, not a collection of individuals
- Predicts how movement in one area will cascade and affect nearby areas
- Detects dangerous feedback loops — compression in one spot triggering a chain reaction elsewhere

---

### Explainable Risk Score

Every alert comes with a clear explanation of what caused it.

- Instead of just showing "DANGER", the system displays: "Density up 38% — speed variance doubled — 74% of crowd moving in same direction"
- Contribution bars show which metrics are driving the alert
- Operators understand exactly what is happening and can respond correctly, not just react to a sound

---

### Digital Twin

A real-time 2D spatial model of the venue is built and updated continuously as detections come in.

- Mirrors the actual crowd positions in a virtual environment
- Runs fast-forward simulations to predict where the crowd will be in the next 60 seconds
- Identifies which exit routes will be blocked under the current crowd trajectory
- Suggests the best evacuation path per zone

---

### Weather-Aware Risk Adjustment

Environmental conditions directly affect crowd safety thresholds.

- Pulls live weather data automatically
- High heat combined with high density raises the risk score — heat stress becomes a compounding factor
- Rain changes crowd mobility and compression patterns, adjusting thresholds accordingly
- Feeds into the predictive model as an additional input variable

---

### LLM-Generated Incident Reports

When an incident is logged, a language model automatically writes a plain-English summary.

- Converts raw numbers into a readable narrative: "At 14:32, Zone B saw density rise 40% in under 90 seconds, combined with a crowd speed spike and direction reversal consistent with early-stage crowd compression."
- Report is immediately available to export as a PDF
- Useful for post-incident review, legal documentation, and management briefings

---

### Mobile Command Center

A lightweight web app accessible from any phone or tablet on the local network.

- Live video stream with all overlays visible
- Full alert feed with acknowledgement controls
- Push notifications when alerts escalate
- No app installation required — just open the URL in any browser
- Designed for security personnel patrolling the venue away from the main control screen

---

## Hardware Requirements

| Setup | Specs |
|---|---|
| Minimum | Any laptop, webcam, 8 GB RAM, CPU only |
| Recommended | NVIDIA GPU (GTX 1660 or better), 16 GB RAM, SSD, HD IP camera |
| Best | NVIDIA RTX GPU or Jetson device, multiple IP cameras, NVMe SSD |

---

## Tech Stack

| Purpose | Tool |
|---|---|
| Language | Python 3.10+ |
| Person Detection | YOLOv8 (Ultralytics) |
| Object Tracking | ByteTrack / DeepSORT |
| Deep Learning | PyTorch |
| Computer Vision | OpenCV |
| Audio Analysis | librosa, PyAudio |
| Edge Inference | ONNX Runtime |
| Visualization | OpenCV, Matplotlib, Pygame |
| Notifications | Twilio (SMS), smtplib (Email), Firebase (Push) |
| Reporting | ReportLab (PDF), pandas (CSV) |
| Mobile App | FastAPI + React |
| Storage | SQLite |
| IDE | VS Code |
| Version Control | Git + GitHub |

---

## Development Phases

**Phase 1 — Detection (Days 1–2)**
Set up environment, install libraries, integrate YOLOv8, display bounding boxes on live feed.

**Phase 2 — Tracking (Days 3–4)**
Integrate ByteTrack, assign persistent IDs, store trajectory history per person.

**Phase 3 — Density and Counting (Days 5–6)**
Implement people counter, zone-based density grid, live statistics panel.

**Phase 4 — Safety Detection (Days 7–8)**
Implement speed spike detection, compression detection, stampede pattern logic, alert engine.

**Phase 5 — Visualization (Days 9–10)**
Build heatmaps, zone overlays, crowd flow arrows, and the full operations dashboard.

**Phase 6 — Logging, Timeline and Reporting (Days 11–12)**
Implement event logger, automatic incident timeline generator, session reports, incident clip recorder, CSV and PDF export.

**Phase 7 — AI Modules (Days 13–16)**
Build and integrate LSTM forecaster, GNN flow model, acoustic panic detector, explainable risk score, lost child detection module.

**Phase 8 — Edge AI and Integration (Days 17–18)**
ONNX export and quantization, offline mode validation, mobile app, notification pipeline, simulation mode, full end-to-end testing and demo preparation.

---

## Demo Flow for Expo

1. Launch system in Edge AI mode — show it running fully offline, no internet
2. Walk into frame — bounding boxes appear, count updates instantly
3. Move around — heatmap starts coloring zones, flow arrows update
4. Place a small object low in frame — lost child detection flags it, alert fires
5. Simulate gradual density increase — WARNING alert fires, yellow overlay appears
6. Simulate panic movement pattern — CRITICAL alert fires, red overlay, siren, voice announcement
7. Show the LSTM prediction gauge — risk was forecast before it visibly happened
8. Show the explainability panel — exactly which metrics caused the alert
9. Pull up the auto-generated incident timeline — full second-by-second breakdown
10. Replay the incident — auto-clipped video plays back with all overlays

---

## Future Extensions

- Integration with smart city emergency management platforms
- Direct API connection to fire department and police dispatch systems
- Automated control of smart barriers and gate systems
- Satellite imagery support for ultra-large area monitoring
- Multi-venue command center dashboard for event organizers
- Federated learning — models improve across venues without sharing raw footage

---

## License

MIT License — free to use, modify, and distribute with attribution.
