#!/bin/bash
# CrowdSafe AI - Smart Launcher
# Automatically checks dependencies and installs if needed

cd "$(dirname "${BASH_SOURCE[0]}")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   CrowdSafe AI — Intelligent Monitor  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

# Quick dependency check
echo -e "${YELLOW}Checking dependencies...${NC}"
python3 -c "import cv2, numpy, scipy, fastapi" 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Missing dependencies detected${NC}"
    echo ""
    echo "Please run one of these first:"
    echo ""
    echo -e "  ${GREEN}./setup.sh${NC}              # Full setup with YOLO model"
    echo -e "  ${GREEN}./install-quick.sh${NC}      # Minimal dependencies"
    echo ""
    echo "Or install manually:"
    echo -e "  ${GREEN}pip install opencv-python numpy scipy filterpy fastapi uvicorn jinja2${NC}"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ All dependencies ready!${NC}"
echo ""

# Determine mode
MODE="LIVE CAMERA"
ARGS=""
if [[ "$1" == "--sim" ]]; then
    MODE="SIMULATION"
    ARGS="--sim"
elif [[ "$1" == "--source" ]]; then
    MODE="VIDEO FILE"
    ARGS="$@"
fi

echo -e "${GREEN}📊 Dashboard:${NC} http://localhost:8000"
echo -e "${YELLOW}🎯 Mode:${NC} $MODE"
echo -e "${YELLOW}💡 Controls:${NC} Press Q to quit, H to hide window"
echo ""
echo "Starting..."
echo ""

python3 main.py $ARGS
