# 🚀 Quick Start Guide

## TL;DR - Just Run It!

```bash
cd "/Users/apple/Desktop/crowd detectiom"
./run.sh                    # Uses real webcam by default
# OR
./run.sh --sim             # Simulation mode (no camera needed)
```

**Dashboard:** http://localhost:8000

---

## ⚡ First Time Setup

### Step 1: Install Dependencies

**Option A: Full Setup (Recommended)**
```bash
./setup.sh
```

**Option B: Quick Install (Minimal deps)**
```bash
./install-quick.sh
```

**Option C: Manual Install**
```bash
python3 -m venv venv
source venv/bin/activate
pip install opencv-python numpy scipy filterpy fastapi uvicorn jinja2 python-multipart aiofiles
```

### Step 2: Run

```bash
# Real webcam (default)
./run.sh

# Simulation mode (no camera)
./run.sh --sim

# Specific camera
./run.sh --source 0        # First webcam
./run.sh --source 1        # Second webcam

# Video file
./run.sh --source /path/to/video.mp4

# RTSP stream
./run.sh --source rtsp://camera-ip/stream

# Headless (dashboard only, no window)
./run.sh --sim --no-window
```

---

## 🎯 Usage Modes

### 1. **Live Camera Mode** (Default)
Uses your real webcam for actual crowd monitoring.

```bash
./run.sh
# or specify camera index
./run.sh --source 0
```

### 2. **Simulation Mode** 
Tests the system without camera using simulated crowd data.

```bash
./run.sh --sim
```

Press keys in simulation window:
- **1** - Normal crowd behavior
- **2** - Building evacuation
- **3** - Dense crowd formation  
- **4** - Panic/stampede scenario

### 3. **Video File Mode**
Process recorded video.

```bash
./run.sh --source myvideo.mp4
```

### 4. **Headless Mode**
Run dashboard only (no OpenCV window).

```bash
./run.sh --sim --no-window
```

---

## 📊 Dashboard Features

Access at **http://localhost:8000**

- **Live Video Feed** - Real-time annotated video
- **People Count** - Current occupancy + percentage
- **Density Metrics** - Area coverage analysis
- **Speed Analysis** - Average movement speed
- **Risk Score** - AI-predicted risk level (0-100%)
- **Direction Entropy** - Crowd flow coherence
- **Acoustic Monitoring** - Sound level detection
- **Anomaly Detection** - Behavior analysis
- **Forecast** - 30s/60s/120s risk predictions
- **Alert Feed** - Live incident timeline
- **Zone Grid** - Spatial risk visualization

### Simulation Controls (Web Dashboard)
Click buttons to trigger scenarios:
- **Normal** - Calm crowd dispersal
- **Building** - Evacuation rush
- **Dense** - High-density compression
- **Panic** - Stampede conditions

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'cv2'"
Run setup first:
```bash
./setup.sh
# or
pip install opencv-python
```

### "Camera cannot be opened"
- Check camera permissions in System Settings
- Try different camera index: `./run.sh --source 1`
- Use simulation mode: `./run.sh --sim`

### Dashboard won't load on port 8000
Change port:
```bash
./run.sh --port 8080
```
Then access: http://localhost:8080

### Running slow on CPU
- Enable GPU acceleration (CUDA)
- Reduce resolution in config/settings.py
- Run headless: `./run.sh --no-window`

---

## 📋 System Requirements

**Minimum:**
- Python 3.9+
- 4GB RAM
- CPU with AVX support
- Webcam (for live mode)

**Recommended:**
- NVIDIA GPU with CUDA
- 8GB RAM
- SSD storage

---

## 🛠️ Advanced Configuration

Edit `config/settings.py` to customize:
- Detection thresholds
- Alert sensitivity
- Zone configurations
- Notification settings (SMS/Email)
- Recording preferences

---

## 📞 Need Help?

Check the full README.md for detailed documentation.

**GitHub Issues:** https://github.com/vincenzo-afk/crowd-detection/issues
