#!/bin/bash
# OMNI-AGENT Build Script - Fixed for PEP 668 externally-managed-environment
set -e

export PIP_BREAK_SYSTEM_PACKAGES=1

echo "🐍 Build starting for OMNI-AGENT..."
echo "📅 $(date)"

if command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

echo "🐍 Using: $($PYTHON --version)"

echo "📦 Upgrading pip (with PEP 668 fix)..."
$PYTHON -m pip install --upgrade pip --break-system-packages --quiet || $PYTHON -m pip install --upgrade pip --quiet || true

# Use lightweight requirements for free tier
REQ="requirements-render.txt"
if [ -f "requirements.txt" ]; then
    if grep -q "torch" requirements.txt; then
        echo "⚠️ requirements.txt contains torch (heavy), using requirements-render.txt"
        REQ="requirements-render.txt"
    else
        REQ="requirements.txt"
    fi
fi

echo "📦 Installing $REQ (lightweight for free tier, PEP 668 fix)..."
$PYTHON -m pip install -r $REQ --break-system-packages --quiet || $PYTHON -m pip install -r $REQ --quiet || $PYTHON -m pip install -r $REQ --break-system-packages || true

echo "📁 Workspace setup..."
mkdir -p workspace/memory workspace/skills workspace/transcripts workspace/sessions workspace/logs
touch workspace/memory/.gitkeep workspace/skills/.gitkeep workspace/transcripts/.gitkeep workspace/sessions/.gitkeep workspace/logs/.gitkeep 2>/dev/null || true

echo "✅ Build complete!"
echo "   Installed: $REQ"
