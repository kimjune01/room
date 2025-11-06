# Room Backend Makefile
# Provides convenient shortcuts for common development tasks

.PHONY: help install test test-unit test-integration test-stress test-coverage test-fast
.PHONY: lint type-check format clean ci dev

# Default target
help:
	@echo "Room Backend Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install       Install dependencies"
	@echo "  dev           Start development server"
	@echo ""
	@echo "Testing:"
	@echo "  test          Run fast tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  test-stress   Run stress tests only"
	@echo "  test-coverage Run tests with coverage report"
	@echo "  test-fast     Run fast tests (exclude slow ones)"
	@echo "  test-all      Run all tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          Run linting checks"
	@echo "  type-check    Run type checking"
	@echo "  format        Format code with black"
	@echo ""
	@echo "CI/CD:"
	@echo "  ci            Run full CI pipeline"
	@echo "  clean         Clean up test artifacts"

# Setup commands
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-test.txt

dev:
	@echo "Starting development server..."
	uvicorn main:app --reload --port 8000

# Testing commands
test:
	@python run_tests.py --fast

test-unit:
	@python run_tests.py --unit

test-integration:
	@python run_tests.py --integration

test-stress:
	@python run_tests.py --stress

test-coverage:
	@python run_tests.py --coverage

test-fast:
	@python run_tests.py --fast

test-all:
	@python run_tests.py --all

# Code quality commands
lint:
	@python run_tests.py --lint

type-check:
	@python run_tests.py --type-check

format:
	@echo "Formatting code with black..."
	@if command -v black >/dev/null 2>&1; then \
		black .; \
		echo "✅ Code formatted"; \
	else \
		echo "⚠️  black not installed, run: pip install black"; \
	fi

# CI/CD commands
ci:
	@python run_tests.py --ci

clean:
	@echo "Cleaning up test artifacts..."
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf __pycache__/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Development workflow shortcuts
quick-check: lint test-fast
	@echo "✅ Quick check complete"

full-check: lint type-check test-coverage
	@echo "✅ Full check complete"

pre-commit: format lint test-fast
	@echo "✅ Pre-commit checks complete"