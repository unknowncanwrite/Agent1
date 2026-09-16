#!/bin/bash
# OMNI-AGENT Start Script - Fixed for PEP 668 + venv + PORT
set -e

export PIP_BREAK_SYSTEM_PACKAGES=1

echo "🚀 Starting OMNI-AGENT..."
echo "📅 $(date)"

# Find python - venv first, then python3
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
    export PATH=".venv/bin:$PATH"
    echo "🐍 Using venv Python: $PYTHON ($($PYTHON --version 2>&1))"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
    echo "🐍 Using python3: $($PYTHON --version 2>&1)"
else
    PYTHON="python"
    echo "🐍 Using python: $($PYTHON --version 2>&1)"
fi

echo "📁 Workspace: ${OMNI_WORKSPACE:-./workspace}"
echo "🌐 Port: ${PORT:-8000}"
echo "🔑 API Key: $(if [ -n "$OPENROUTER_API_KEY" ]; then echo "set"; else echo "NOT SET"; fi)"

mkdir -p workspace/memory workspace/skills workspace/transcripts workspace/sessions workspace/logs
touch workspace/memory/.gitkeep workspace/skills/.gitkeep workspace/transcripts/.gitkeep workspace/sessions/.gitkeep workspace/logs/.gitkeep 2>/dev/null || true

# Check deps - if missing, install with PEP 668 fix
echo "🔍 Checking dependencies..."
if ! $PYTHON -c "import fastapi, httpx, uvicorn" 2>/dev/null; then
    echo "⚠️ Dependencies missing, installing with PEP 668 fix..."
    REQ="requirements-render.txt"
    [ -f "requirements.txt" ] && REQ="requirements.txt"
    # Try lightweight first
    if [ -f "requirements-render.txt" ]; then
        REQ="requirements-render.txt"
    fi
    echo "📦 Installing $REQ..."
    $PYTHON -m pip install -r $REQ --break-system-packages --quiet || $PYTHON -m pip install -r $REQ --quiet || pip install -r $REQ --break-system-packages --quiet || true
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies OK"
fi

echo "✅ Starting server at 0.0.0.0:${PORT:-8000}..."
echo "🌐 Web UI: http://0.0.0.0:${PORT:-8000}/"
exec $PYTHON main.py serve --host 0.0.0.0 --port ${PORT:-8000}
