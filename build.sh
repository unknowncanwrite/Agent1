#!/bin/bash
set -e
echo "🐍 Build starting for OMNI-AGENT..."
echo "📅 $(date)"

if command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

echo "🐍 Using: $($PYTHON --version)"
echo "📦 Upgrading pip..."
$PYTHON -m pip install --upgrade pip --quiet 2>/dev/null || $PYTHON -m pip install --upgrade pip

# Use lightweight requirements for Render free tier (no torch)
REQ="requirements-render.txt"
if [ -f "requirements.txt" ]; then
    # Check if requirements.txt is lightweight (no torch)
    if grep -q "torch" requirements.txt; then
        echo "⚠️ requirements.txt contains torch (heavy), using requirements-render.txt for free tier"
        REQ="requirements-render.txt"
    else
        REQ="requirements.txt"
    fi
fi

echo "📦 Installing $REQ (lightweight for free tier)..."
$PYTHON -m pip install -r $REQ --quiet 2>/dev/null || $PYTHON -m pip install -r $REQ

echo "📁 Workspace setup..."
mkdir -p workspace/memory workspace/skills workspace/transcripts workspace/sessions workspace/logs
touch workspace/memory/.gitkeep workspace/skills/.gitkeep workspace/transcripts/.gitkeep workspace/sessions/.gitkeep workspace/logs/.gitkeep 2>/dev/null || true

echo "✅ Build complete!"
echo "   Build file: $REQ"
echo "   Start: ./start.sh"
