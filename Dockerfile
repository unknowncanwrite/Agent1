FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt || true
ENV AGENT1_WORKSPACE=/app/workspace AGENT1_APPROVAL=safe
EXPOSE 8080
CMD ["python", "-m", "agent1.cli", "serve", "--port", "8080"]
