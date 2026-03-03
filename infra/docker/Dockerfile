FROM python:3.12-slim

WORKDIR /app

# Install system deps + Terraform CLI (needed by terraform_validate and deploy tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl gnupg && \
    curl -fsSL https://apt.releases.hashicorp.com/gpg | \
        gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com bookworm main" \
        > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y --no-install-recommends terraform && \
    apt-get purge -y curl gnupg && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

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
