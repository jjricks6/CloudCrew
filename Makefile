.PHONY: check test lint format typecheck security arch-test file-size-check \
       install install-hooks clean checkov-scan dashboard-check \
       bootstrap-init bootstrap-apply tf-init tf-plan tf-apply tf-destroy tf-validate \
       docker-build docker-push deploy teardown dashboard-deploy

# Run ALL CI checks locally — agents MUST run this before committing and pushing
check: format lint typecheck test security file-size-check tf-validate checkov-scan dashboard-check

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

# Checkov security scan on Terraform code (uses .checkov.yml for dev suppressions)
checkov-scan:
	checkov -d infra/ --framework terraform --quiet --compact --config-file infra/terraform/.checkov.yml

# --- Dashboard: frontend lint, typecheck, build ---

dashboard-check:
	cd dashboard && npx tsc -b && npx eslint . && npx vite build

# --- Docker: ECS phase runner image ---

docker-build:
	docker buildx build --platform linux/amd64 --provenance=false -t cloudcrew-phase-runner:latest -f infra/docker/Dockerfile .

docker-push:
	@echo "Authenticating with ECR..."
	@aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $$(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
	$(eval ECR_URI := $(shell terraform -chdir=infra/terraform output -raw ecr_repository_url))
	docker tag cloudcrew-phase-runner:latest $(ECR_URI):latest
	docker push $(ECR_URI):latest

# --- Full deploy: one command to stand up everything ---
#
# Order matters:
#   1. tf-init          — initialize Terraform providers/state
#   2. tf-apply (1st)   — creates infra + ECR repo (Lambdas may fail — no image yet)
#   3. docker-build     — build single-platform amd64 image
#   4. docker-push      — push image to ECR
#   5. tf-apply (2nd)   — creates remaining Lambdas + Step Functions
#   6. dashboard-deploy — build dashboard with new URLs, sync to S3, invalidate CDN
#
deploy:
	@echo "=== Step 1/6: Terraform init ==="
	terraform -chdir=infra/terraform init
	@echo ""
	@echo "=== Step 2/6: Terraform apply (infra + ECR) ==="
	terraform -chdir=infra/terraform apply -var-file=terraform.tfvars
	@echo ""
	@echo "=== Step 3/6: Docker build (linux/amd64) ==="
	docker buildx build --platform linux/amd64 --provenance=false -t cloudcrew-phase-runner:latest -f infra/docker/Dockerfile .
	@echo ""
	@echo "=== Step 4/6: Docker push to ECR ==="
	@aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $$(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
	$(eval ECR_URI := $(shell terraform -chdir=infra/terraform output -raw ecr_repository_url))
	docker tag cloudcrew-phase-runner:latest $(ECR_URI):latest
	docker push $(ECR_URI):latest
	@echo ""
	@echo "=== Step 5/6: Terraform apply (Lambdas + Step Functions) ==="
	terraform -chdir=infra/terraform apply -var-file=terraform.tfvars
	@echo ""
	@echo "=== Step 6/6: Dashboard deploy ==="
	cd dashboard && npm run build
	$(eval BUCKET := $(shell terraform -chdir=infra/terraform output -raw dashboard_bucket))
	$(eval CF_ID := $(shell terraform -chdir=infra/terraform output -raw cloudfront_distribution_id))
	aws s3 sync dashboard/dist s3://$(BUCKET) --delete
	aws cloudfront create-invalidation --distribution-id $(CF_ID) --paths "/*"
	@echo ""
	@echo "=== Deploy complete ==="
	@echo "Dashboard: https://$$(terraform -chdir=infra/terraform output -raw cloudfront_domain)"
	@echo "API:       $$(terraform -chdir=infra/terraform output -raw api_gateway_url)"
	@echo "WebSocket: $$(terraform -chdir=infra/terraform output -raw websocket_api_url)"

# Deploy just the dashboard (build + S3 sync + CloudFront invalidation)
dashboard-deploy:
	cd dashboard && npm run build
	$(eval BUCKET := $(shell terraform -chdir=infra/terraform output -raw dashboard_bucket))
	$(eval CF_ID := $(shell terraform -chdir=infra/terraform output -raw cloudfront_distribution_id))
	aws s3 sync dashboard/dist s3://$(BUCKET) --delete
	aws cloudfront create-invalidation --distribution-id $(CF_ID) --paths "/*"
	@echo "Dashboard deployed: https://$$(terraform -chdir=infra/terraform output -raw cloudfront_domain)"

# --- Full teardown: stop everything, then destroy ---
#
# Stops running ECS tasks and Step Functions executions first,
# then runs terraform destroy. Without this, the internet gateway
# and state machine deletions hang or fail.
#
teardown:
	@echo "=== Stopping running ECS tasks ==="
	@CLUSTER=$$(terraform -chdir=infra/terraform output -raw ecs_cluster_arn 2>/dev/null) && \
	if [ -n "$$CLUSTER" ]; then \
		TASKS=$$(aws ecs list-tasks --cluster "$$CLUSTER" --query 'taskArns[]' --output text 2>/dev/null) && \
		if [ -n "$$TASKS" ]; then \
			for task in $$TASKS; do \
				echo "  Stopping $$task"; \
				aws ecs stop-task --cluster "$$CLUSTER" --task "$$task" --reason "Teardown" --output text --query 'task.lastStatus' 2>/dev/null; \
			done; \
			echo "  Waiting for tasks to stop..."; \
			sleep 30; \
		else \
			echo "  No running tasks"; \
		fi; \
	else \
		echo "  No ECS cluster found in state"; \
	fi
	@echo ""
	@echo "=== Stopping running Step Functions executions ==="
	@SFN_ARN=$$(terraform -chdir=infra/terraform output -raw step_functions_arn 2>/dev/null) && \
	if [ -n "$$SFN_ARN" ]; then \
		EXECS=$$(aws stepfunctions list-executions --state-machine-arn "$$SFN_ARN" --status-filter RUNNING --query 'executions[].executionArn' --output text 2>/dev/null) && \
		if [ -n "$$EXECS" ]; then \
			for exec in $$EXECS; do \
				echo "  Stopping $$exec"; \
				aws stepfunctions stop-execution --execution-arn "$$exec" --cause "Teardown" > /dev/null 2>&1; \
			done; \
		else \
			echo "  No running executions"; \
		fi; \
	else \
		echo "  No state machine found in state"; \
	fi
	@echo ""
	@echo "=== Terraform destroy ==="
	terraform -chdir=infra/terraform destroy -var-file=terraform.tfvars
