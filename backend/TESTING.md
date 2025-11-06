# Room Backend Testing Guide

This document describes the comprehensive testing infrastructure for the Room Backend.

## Overview

The test suite is designed to ensure backend stability and catch critical issues like:
- WebSocket connection management errors
- YouTube synchronization problems
- Concurrent user scenarios
- Room state consistency issues

## Test Structure

```
tests/
├── __init__.py                     # Test package
├── conftest.py                     # Shared fixtures and configuration
├── test_basic.py                   # Basic infrastructure tests
├── unit/                           # Unit tests
│   ├── __init__.py
│   ├── test_connection_manager.py  # ConnectionManager unit tests
│   └── test_youtube_activity.py    # YouTube activity unit tests
├── integration/                    # Integration tests
│   ├── __init__.py
│   ├── test_websocket_integration.py  # WebSocket integration tests
│   └── test_youtube_integration.py    # YouTube integration tests
└── stress/                         # Stress/load tests
    ├── __init__.py
    └── test_concurrent_users.py    # Concurrent user stress tests
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- Mock external dependencies
- Test individual components
- **Files**: `tests/unit/`

### Integration Tests (`@pytest.mark.integration`)
- Test component interactions
- Use real WebSocket mocks
- End-to-end workflows
- **Files**: `tests/integration/`

### Stress Tests (`@pytest.mark.stress`)
- High-load scenarios
- Concurrent user simulations
- Performance benchmarks
- **Files**: `tests/stress/`

### Slow Tests (`@pytest.mark.slow`)
- Tests taking >5 seconds
- Usually stress tests
- Excluded from fast test runs

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r requirements-test.txt
# OR
python run_tests.py --install
# OR
make install
```

### Quick Commands

```bash
# Fast tests (recommended for development)
make test
python run_tests.py --fast

# Specific test types
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-stress        # Stress tests only

# All tests
make test-all
python run_tests.py --all

# With coverage
make test-coverage
python run_tests.py --coverage

# Code quality
make lint
make type-check
make format

# Full CI pipeline
make ci
python run_tests.py --ci
```

### Advanced Usage

```bash
# Verbose output
python run_tests.py --unit -v

# Run specific test files
pytest tests/unit/test_connection_manager.py -v

# Run specific test methods
pytest tests/unit/test_connection_manager.py::TestConnectionManager::test_connect_new_room -v

# Run tests matching pattern
pytest -k "connection" -v

# Run tests by marker
pytest -m "unit" -v
pytest -m "not slow" -v
```

## Key Test Areas

### 1. Connection Management
**File**: `tests/unit/test_connection_manager.py`
- User connection/disconnection
- Room creation/cleanup
- Host transfer mechanisms
- Broadcasting and messaging
- Error handling during disconnections

**Critical scenarios tested**:
- Set changed size during iteration errors
- KeyError on disconnect
- Proper resource cleanup

### 2. YouTube Activity Synchronization
**File**: `tests/unit/test_youtube_activity.py`
- Democratic play/pause controls (any user)
- Master-only controls (load, seek, rate)
- Buffering coordination
- State synchronization
- Permission system

**Integration tests** (`tests/integration/test_youtube_integration.py`):
- Full session workflows
- Master control transfers
- Concurrent actions
- Error scenarios

### 3. WebSocket Integration
**File**: `tests/integration/test_websocket_integration.py`
- Connection lifecycle
- Message ordering
- Error recovery
- Host transfer flows

### 4. Stress Testing
**File**: `tests/stress/test_concurrent_users.py`
- High concurrent connections (50+ users)
- Rapid room creation/destruction
- Connection churn patterns
- Memory leak prevention
- Performance benchmarks

## Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
asyncio_mode = auto
timeout = 30
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    -ra

markers =
    unit: Unit tests
    integration: Integration tests
    stress: Stress/load tests
    slow: Tests that take longer than 5 seconds
```

### Test Fixtures
**File**: `tests/conftest.py`

Key fixtures:
- `clean_manager`: Clean ConnectionManager instance
- `mock_websocket`: Single mock WebSocket
- `mock_websockets`: Multiple mock WebSockets
- `youtube_activity`: YouTube activity with message handler
- `sample_video_data`: Test video data
- `sample_users`: Test user data

## Writing New Tests

### Unit Test Template
```python
import pytest
from unittest.mock import AsyncMock

class TestYourComponent:
    @pytest.mark.unit
    async def test_your_feature(self, clean_manager):
        # Arrange
        manager = clean_manager

        # Act
        result = await manager.your_method()

        # Assert
        assert result is expected
```

### Integration Test Template
```python
import pytest
from unittest.mock import AsyncMock

class TestYourIntegration:
    @pytest.mark.integration
    async def test_your_workflow(self):
        # Test end-to-end workflow
        pass
```

### Stress Test Template
```python
import pytest
import asyncio

class TestYourStress:
    @pytest.mark.stress
    @pytest.mark.slow
    async def test_high_load(self):
        # Test high-load scenario
        pass
```

## Continuous Integration

The CI pipeline (`make ci` or `python run_tests.py --ci`) runs:

1. **Install Dependencies**: Install test requirements
2. **Lint Checks**: Code quality with flake8
3. **Type Checks**: Static analysis with mypy
4. **Fast Tests**: Quick unit and integration tests
5. **Coverage Tests**: Full test suite with coverage report

### Coverage Requirements
- Minimum coverage: 80%
- Report formats: Terminal + HTML
- HTML report: `htmlcov/index.html`

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the backend directory
2. **Async Test Failures**: Use `@pytest.mark.asyncio` for async tests
3. **Fixture Issues**: Check fixture scope and dependencies
4. **Mock Problems**: Ensure proper AsyncMock usage for async methods

### Debug Commands
```bash
# Run with extra verbose output
pytest -vvv tests/your_test.py

# Run single test with prints
pytest -s tests/your_test.py::test_function

# Run with debugger
pytest --pdb tests/your_test.py

# Show fixtures
pytest --fixtures tests/
```

## Performance Expectations

### Connection Benchmarks
- 100 connections: < 2.0s
- Broadcast to 100 users: < 0.5s
- 100 disconnections: < 2.0s

### Test Execution Times
- Unit tests: < 0.1s each
- Integration tests: < 1.0s each
- Stress tests: 1-10s each (marked as slow)

## Contributing

When adding new features:

1. **Write unit tests first** (TDD approach)
2. **Add integration tests** for complex workflows
3. **Include stress tests** for scalability-critical features
4. **Update this documentation** if adding new test categories
5. **Ensure all tests pass** before submitting

Remember: Tests are documentation of expected behavior. Write them clearly and maintain them actively.