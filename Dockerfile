FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create workspace
RUN mkdir -p workspace/memory workspace/skills workspace/transcripts workspace/sessions workspace/logs && \
    touch workspace/memory/.gitkeep workspace/skills/.gitkeep workspace/transcripts/.gitkeep workspace/sessions/.gitkeep workspace/logs/.gitkeep

ENV PYTHONPATH=/app
ENV OMNI_WORKSPACE=/app/workspace
ENV PORT=10000

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:$PORT/api/health || exit 1

CMD ["sh", "-c", "python3 main.py serve --host 0.0.0.0 --port ${PORT:-10000}"]
