#!/bin/bash
# OMNI-AGENT Start Script - Bulletproof for Render
set -e

echo "🚀 Starting OMNI-AGENT..."
echo "📅 $(date)"

# Find best Python - venv first
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
    export PATH=".venv/bin:$PATH"
    echo "🐍 Using venv Python: $PYTHON ($($PYTHON --version))"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
    echo "🐍 Using python3: $($PYTHON --version)"
else
    PYTHON="python"
    echo "🐍 Using python: $($PYTHON --version 2>&1)"
fi

echo "📁 Workspace: ${OMNI_WORKSPACE:-./workspace}"
echo "🌐 Port: ${PORT:-8000}"
echo "🔑 API Key: $(if [ -n "$OPENROUTER_API_KEY" ]; then echo "set"; else echo "NOT SET - UI loads but chat fails"; fi)"

mkdir -p workspace/memory workspace/skills workspace/transcripts workspace/sessions workspace/logs
touch workspace/memory/.gitkeep workspace/skills/.gitkeep workspace/transcripts/.gitkeep workspace/sessions/.gitkeep workspace/logs/.gitkeep 2>/dev/null || true

# Ensure deps - try to import, if fails install
echo "🔍 Checking dependencies..."
if ! $PYTHON -c "import fastapi, httpx, uvicorn" 2>/dev/null; then
    echo "⚠️ Dependencies missing, installing..."
    REQ="requirements-render.txt"
    [ -f "requirements.txt" ] && REQ="requirements.txt"
    echo "📦 Installing $REQ..."
    $PYTHON -m pip install -r $REQ --quiet || $PYTHON -m pip install -r $REQ --break-system-packages --quiet || pip install -r $REQ --quiet
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies OK"
fi

echo "✅ Starting server at 0.0.0.0:${PORT:-8000}..."
echo "🌐 Web UI: http://0.0.0.0:${PORT:-8000}/"
echo "📚 API Docs: http://0.0.0.0:${PORT:-8000}/docs"
exec $PYTHON main.py serve --host 0.0.0.0 --port ${PORT:-8000}
