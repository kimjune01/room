#!/usr/bin/env python3
"""
Test Runner for Room Activities System
Runs all tests in the organized test structure
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path


def run_test_file(test_file: Path) -> tuple[str, bool]:
    """Run a single test file and return results"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file.name}")
    print('='*60)

    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=test_file.parent.parent.parent,  # Run from root directory
            capture_output=False,
            text=True
        )

        success = result.returncode == 0
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{test_file.name}: {status}")
        return test_file.name, success

    except Exception as e:
        print(f"❌ ERROR running {test_file.name}: {e}")
        return test_file.name, False


def main():
    """Run all tests in the test directory structure"""
    print("🧪 Room Activities System - Organized Test Suite")
    print("=" * 60)

    # Find all test files
    tests_dir = Path(__file__).parent
    test_files = []

    # Integration tests
    integration_dir = tests_dir / "integration"
    if integration_dir.exists():
        test_files.extend(sorted(integration_dir.glob("test_*.py")))

    if not test_files:
        print("❌ No test files found!")
        return False

    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.relative_to(tests_dir)}")

    # Run all tests
    results = []
    for test_file in test_files:
        name, success = run_test_file(test_file)
        results.append((name, success))

    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Results Summary")
    print('='*60)

    passed = 0
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {name}: {status}")
        if success:
            passed += 1

    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")

    if passed == total:
        print("\n🎉 All tests passed! System is working correctly.")
        return True
    else:
        print(f"\n💥 {total - passed} test(s) failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)