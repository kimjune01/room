#!/usr/bin/env python3
"""
Automated test runner for the room backend.
Provides various testing modes and configurations.
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(cmd, description="", check=True):
    """Run a shell command with proper error handling."""
    print(f"\n🔄 {description}")
    print(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stdout:
            print(f"   Stdout: {e.stdout.strip()}")
        if e.stderr:
            print(f"   Stderr: {e.stderr.strip()}")
        return False


def install_dependencies():
    """Install test dependencies."""
    return run_command(
        ["pip", "install", "-r", "requirements-test.txt"],
        "Installing test dependencies"
    )


def run_unit_tests(verbose=False):
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "tests/unit/", "-m", "unit"]
    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Running unit tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "tests/integration/", "-m", "integration"]
    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Running integration tests")


def run_stress_tests(verbose=False):
    """Run stress tests."""
    cmd = ["python", "-m", "pytest", "tests/stress/", "-m", "stress"]
    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Running stress tests")


def run_all_tests(verbose=False):
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "tests/"]
    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Running all tests")


def run_coverage_tests():
    """Run tests with coverage reporting."""
    cmd = [
        "python", "-m", "pytest", "tests/",
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=80"
    ]

    success = run_command(cmd, "Running tests with coverage")
    if success:
        print("\n📊 Coverage report generated in htmlcov/index.html")
    return success


def run_fast_tests():
    """Run fast tests only (exclude slow tests)."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "not slow"]

    return run_command(cmd, "Running fast tests only")


def run_lint_checks():
    """Run code quality checks."""
    success = True

    # Check if files exist before running
    python_files = list(Path(".").glob("**/*.py"))
    if not python_files:
        print("No Python files found to lint")
        return True

    # Try flake8 first
    if run_command(["which", "flake8"], check=False):
        success &= run_command(
            ["flake8", "--max-line-length=100", "--ignore=E203,W503"] + [str(f) for f in python_files],
            "Running flake8 linting",
            check=False
        )

    # Try black check
    if run_command(["which", "black"], check=False):
        success &= run_command(
            ["black", "--check", "."],
            "Checking code formatting with black",
            check=False
        )

    return success


def run_type_checks():
    """Run type checking."""
    if run_command(["which", "mypy"], check=False):
        return run_command(
            ["mypy", ".", "--ignore-missing-imports"],
            "Running type checks with mypy",
            check=False
        )
    else:
        print("⚠️  mypy not found, skipping type checks")
        return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Room Backend Test Runner")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--stress", action="store_true", help="Run stress tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--lint", action="store_true", help="Run linting checks")
    parser.add_argument("--type-check", action="store_true", help="Run type checking")
    parser.add_argument("--ci", action="store_true", help="Run full CI pipeline")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Change to script directory
    os.chdir(Path(__file__).parent)

    success = True

    if args.install or args.ci:
        success &= install_dependencies()

    if args.unit:
        success &= run_unit_tests(args.verbose)
    elif args.integration:
        success &= run_integration_tests(args.verbose)
    elif args.stress:
        success &= run_stress_tests(args.verbose)
    elif args.all:
        success &= run_all_tests(args.verbose)
    elif args.coverage:
        success &= run_coverage_tests()
    elif args.fast:
        success &= run_fast_tests()
    elif args.ci:
        # Full CI pipeline
        print("\n🚀 Running full CI pipeline...")
        success &= run_lint_checks()
        success &= run_type_checks()
        success &= run_fast_tests()  # Run fast tests first
        if success:
            success &= run_coverage_tests()  # Full coverage if fast tests pass
    elif args.lint:
        success &= run_lint_checks()
    elif args.type_check:
        success &= run_type_checks()
    else:
        # Default: run fast tests
        print("No specific test type specified, running fast tests...")
        success &= run_fast_tests()

    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())