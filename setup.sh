#!/bin/bash
# ────────────────────────────────────────────────────────────────
# CrowdSafe AI — One-click Setup Script
# ────────────────────────────────────────────────────────────────

set -e
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════╗"
echo "║   CrowdSafe AI — Installation & Setup            ║"
echo "║   Intelligent Crowd Safety & Stampede Prevention ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Python check
python3 --version >/dev/null 2>&1 || { echo -e "${RED}Python 3 not found!${NC}"; exit 1; }

# Virtual environment
if [ ! -d "venv" ]; then
  echo -e "${YELLOW}Creating virtual environment...${NC}"
  python3 -m venv venv
fi

source venv/bin/activate

echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip -q

echo -e "${YELLOW}Installing dependencies... (this may take a few minutes)${NC}"
pip install -r requirements.txt -q

# Create necessary dirs
mkdir -p models logs recordings reports config assets

# Download YOLOv8n model
echo -e "${YELLOW}Downloading YOLOv8n model...${NC}"
python3 -c "
from ultralytics import YOLO
import shutil, os
m = YOLO('yolov8n.pt')
dest = 'models/yolov8n.pt'
if not os.path.exists(dest):
    src = m.ckpt_path if hasattr(m,'ckpt_path') else 'yolov8n.pt'
    try: shutil.copy(src, dest)
    except: pass
print('Model ready.')
" 2>/dev/null || echo "Model will download on first run."

echo -e "${GREEN}${BOLD}"
echo "✅ Setup complete!"
echo ""
echo "To run the system:"
echo ""
echo "  Simulation mode (no camera needed):"
echo "    ./run.sh --sim"
echo ""
echo "  Live webcam:"
echo "    ./run.sh --source 0"
echo ""
echo "  Video file:"
echo "    ./run.sh --source path/to/video.mp4"
echo ""
echo "  Headless (dashboard only, no window):"
echo "    ./run.sh --sim --no-window"
echo ""
echo "  Dashboard URL: http://localhost:8000"
echo -e "${NC}"
