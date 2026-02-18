FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (cached layer)
# awslambdaric: Lambda Runtime Interface Client — enables the same image to
# serve as a Lambda container image (entrypoint overridden in Terraform).
COPY pyproject.toml ./
RUN pip install --no-cache-dir . awslambdaric

# Copy application code
COPY src/ ./src/

# Default entrypoint: ECS phase runner.
# Lambda functions override via Terraform image_config:
#   entry_point = ["python", "-m", "awslambdaric"]
#   command     = ["src.phases.sfn_handlers.route"]
CMD ["python", "-m", "src.phases"]
