#!/bin/bash
# ────────────────────────────────────────────────────────────────
# CrowdSafe AI — Quick Launch Script
# ────────────────────────────────────────────────────────────────

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Activate venv if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "🚀 Launching CrowdSafe AI..."
echo "📊 Dashboard: http://localhost:8000"
echo "Press Q in the video window (or Ctrl+C) to stop."
echo ""

python3 main.py "$@"
