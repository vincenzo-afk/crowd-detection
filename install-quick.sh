#!/bin/bash
# Quick install for impatient users
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "🚀 Installing minimal dependencies..."

source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate

pip install --quiet opencv-python numpy scipy filterpy fastapi uvicorn jinja2 python-multipart aiofiles

echo ""
echo "✅ Installation complete!"
echo ""
echo "Now run:"
echo "  ./run.sh --sim          # Simulation mode"
echo "  ./run.sh --source 0     # Real webcam"
echo ""
