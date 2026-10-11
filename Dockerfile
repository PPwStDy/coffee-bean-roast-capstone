FROM python:3.12-slim AS runtime

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "Docker image user" appuser

WORKDIR /app

# Install Python requirements
COPY requirements-serve.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements-serve.lock

# Copy application code and model artifacts
COPY src/ src/
COPY service/ service/
COPY tests/fixtures/ tests/fixtures/
COPY reports/model.onnx reports/model.onnx
COPY reports/model_metadata.json reports/model_metadata.json

# Set ownership
RUN chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    MODEL_PATH=reports/model.onnx \
    MODEL_METADATA_PATH=reports/model_metadata.json

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ready || exit 1

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8080"]
