.PHONY: check test lint format typecheck security arch-test file-size-check \
       install install-hooks clean checkov-scan \
       bootstrap-init bootstrap-apply tf-init tf-plan tf-apply tf-destroy tf-validate \
       docker-build docker-push

# Run ALL CI checks locally — agents MUST run this before committing and pushing
check: format lint typecheck test security file-size-check tf-validate checkov-scan

# Install dependencies
install:
	pip install -e ".[dev]"

# Install pre-commit hooks
install-hooks:
	pre-commit install

# Format code (auto-fix)
format:
	ruff format src/ tests/

# Lint code
lint:
	ruff check src/ tests/

# Lint with auto-fix
lint-fix:
	ruff check --fix src/ tests/

# Type check (strict)
typecheck:
	mypy src/

# Run tests with coverage
test:
	pytest tests/ -m "not integration and not e2e" --cov=src --cov-report=term-missing

# Run only architecture boundary tests
arch-test:
	pytest tests/architecture/ -v

# Run integration tests (requires AWS credentials)
test-integration:
	pytest tests/ -m integration --cov=src --cov-report=term-missing

# Security scan
security:
	bandit -r src/ -c pyproject.toml

# Check for oversized Python files (>500 lines)
file-size-check:
	@oversized=$$(find src/ -name "*.py" -exec awk 'END{if(NR>500)print FILENAME": "NR" lines"}' {} \;); \
	if [ -n "$$oversized" ]; then \
		echo "Files exceeding 500 line limit:"; \
		echo "$$oversized"; \
		exit 1; \
	fi; \
	echo "All files within size limits"

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage

# --- Terraform: Bootstrap (one-time state backend setup) ---

bootstrap-init:
	terraform -chdir=infra/bootstrap init

bootstrap-apply:
	terraform -chdir=infra/bootstrap apply

# --- Terraform: Main infrastructure ---

tf-init:
	terraform -chdir=infra/terraform init

tf-plan:
	terraform -chdir=infra/terraform plan -var-file=terraform.tfvars

tf-apply:
	terraform -chdir=infra/terraform apply -var-file=terraform.tfvars

tf-destroy:
	terraform -chdir=infra/terraform destroy -var-file=terraform.tfvars

# Validate Terraform (no AWS credentials needed)
tf-validate:
	terraform -chdir=infra/bootstrap fmt -check
	terraform -chdir=infra/terraform fmt -check
	terraform -chdir=infra/bootstrap init -backend=false
	terraform -chdir=infra/bootstrap validate
	terraform -chdir=infra/terraform init -backend=false
	terraform -chdir=infra/terraform validate

# Checkov security scan on Terraform code
checkov-scan:
	checkov -d infra/ --framework terraform --quiet --compact

# --- Docker: ECS phase runner image ---

docker-build:
	docker build -t cloudcrew-phase-runner -f infra/docker/Dockerfile .

docker-push:
	@echo "Pushing to ECR — ensure you have run: aws ecr get-login-password | docker login"
	$(eval ECR_URI := $(shell terraform -chdir=infra/terraform output -raw ecr_repository_url))
	docker tag cloudcrew-phase-runner:latest $(ECR_URI):latest
	docker push $(ECR_URI):latest
