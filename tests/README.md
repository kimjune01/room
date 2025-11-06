# Tests

Organized test suite for the Room Activities System.

## Structure

```
tests/
├── run_tests.py              # Main test runner
├── integration/
│   ├── test_basic_functionality.py   # Basic system functionality
│   ├── test_youtube_sync.py          # YouTube synchronization tests
│   └── test_new_user_sync.py         # New user sync behavior tests
└── README.md
```

## Running Tests

### All Tests
```bash
python tests/run_tests.py
```

### Individual Tests
```bash
python tests/integration/test_youtube_sync.py
python tests/integration/test_new_user_sync.py
```

## Test Categories

### Integration Tests
- **test_youtube_sync.py**: Complete YouTube IFrame API integration testing
  - Basic video sync between multiple clients
  - Master control permissions
  - Multi-client synchronization

- **test_new_user_sync.py**: New user synchronization behavior
  - Joining paused video rooms
  - Joining active video rooms
  - Non-disruptive join behavior

- **test_basic_functionality.py**: Core system functionality
  - Basic WebSocket connections
  - Host permissions
  - Activity switching
  - Snake game basics

## Requirements

- Backend server running on port 8001
- All tests require WebSocket connectivity

## Test Coverage

The test suite covers:
- ✅ WebSocket connectivity and room management
- ✅ Host permissions and activity control
- ✅ YouTube video synchronization across clients
- ✅ New user sync behavior without disruption
- ✅ Multi-client real-time state synchronization
- ✅ Snake game basic functionality

Total test execution time: ~30-60 seconds