# Testing Guide for WebSocket Chat Application

Comprehensive testing documentation for smoke tests, E2E tests, and activity switching functionality.

## 🧪 Test Suite Overview

Our testing strategy covers multiple layers to ensure robust activity switching functionality:

### Test Suites

1. **🔥 Smoke Tests** (`test_smoke.py`)
   - Basic WebSocket connection functionality
   - Host assignment and permissions
   - Multi-room isolation
   - Connection lifecycle management

2. **🎯 E2E Activity Tests** (`test_e2e_activities.py`)
   - Activity switching workflows
   - Host control for room activities
   - Multi-user activity participation
   - Activity state persistence

3. **👑 Host Permission Tests** (`test_host_permissions.py`)
   - Host-only action validation
   - Permission enforcement under load
   - Host state persistence
   - Edge cases and invalid actions

4. **👥 Multi-User Scenario Tests** (`test_multi_user_scenarios.py`)
   - Large room capacity (10+ users)
   - Concurrent activity actions
   - User lifecycle during activities
   - High message volume performance

## 🚀 Quick Start

### Prerequisites

1. **Backend Server Running**:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

2. **Install Test Dependencies**:
   ```bash
   pip install -r test_requirements.txt
   ```

### Running Tests

#### All Tests
```bash
python test_runner.py
```

#### Quick Tests (Smoke + Host Permissions)
```bash
python test_runner.py --quick
```

#### Individual Test Suites
```bash
python test_runner.py --suite smoke
python test_runner.py --suite host_permissions
python test_runner.py --suite e2e_activities
python test_runner.py --suite multi_user
```

#### Generate Test Report
```bash
python test_runner.py --report
```

## 📊 Test Results Interpretation

### ✅ All Tests Passing
- System is ready for production
- All activity switching functionality works
- Host controls are secure
- Multi-user scenarios handle correctly

### ❌ Test Failures by Category

**Smoke Tests Failing**:
- Basic WebSocket functionality is broken
- Fix these first before other tests
- Check server connectivity and basic message flow

**Host Permission Tests Failing**:
- Security vulnerabilities in host controls
- Non-hosts may be able to perform unauthorized actions
- Host state management issues

**E2E Activity Tests Failing**:
- Activity switching workflow problems
- State synchronization issues
- UI/backend integration problems

**Multi-User Tests Failing**:
- Performance issues under load
- Concurrent action handling problems
- Memory leaks or connection issues

## 🔧 Test Infrastructure

### Test Client Architecture

Each test suite uses specialized client classes:

```python
class TestClient:
    """Base test client with WebSocket connection management"""
    - Connection/disconnection handling
    - Message sending/receiving
    - Timeout management
    - State tracking

class E2ETestClient(TestClient):
    """Extended for activity testing"""
    - Activity state tracking
    - Host role detection
    - Activity action simulation

class HostPermissionTestClient(TestClient):
    """Specialized for permission testing"""
    - Permission validation
    - Host action attempts
    - Error response handling

class MultiUserTestClient(TestClient):
    """Optimized for multi-user scenarios"""
    - Performance metrics tracking
    - Concurrent action support
    - Lifecycle state management
```

### Message Flow Testing

Tests validate complete message flows:

1. **Send Message** → WebSocket → **Server Processing** → **Broadcast** → **All Clients Receive**
2. **Host Action** → **Permission Check** → **State Update** → **Notify All Users**
3. **Activity Switch** → **Validate Permissions** → **Stop Old Activity** → **Start New Activity** → **Update All UIs**

## 📈 Performance Benchmarks

### Expected Performance (Current System)

- **Connection Time**: < 100ms per user
- **Message Latency**: < 50ms end-to-end
- **Activity Switch**: < 200ms for all users
- **Room Capacity**: 50+ concurrent users per room
- **Message Throughput**: 1000+ messages/second

### Load Testing Scenarios

```python
# Large room test (12 users)
- Each user sends 10 messages
- Total: 120 messages + echoes + broadcasts
- Expected: < 5 seconds total time

# Concurrent actions test (6 users)
- Simultaneous activity actions
- Activity switching under load
- Expected: No timeouts or errors

# High message volume (8 users, 10 messages each)
- 80 total messages
- Each user receives 80 messages (own + others)
- Expected: < 10 seconds completion
```

## 🐛 Debugging Failed Tests

### Common Issues and Solutions

#### WebSocket Connection Failures
```bash
# Check server is running
curl http://localhost:8000

# Check WebSocket endpoint
wscat -c ws://localhost:8000/ws/test/user
```

#### Message Timeout Issues
- Increase timeout values in test clients
- Check server logs for processing delays
- Verify message routing logic

#### Permission Test Failures
- Check host assignment logic
- Verify permission validation in backend
- Test with browser developer tools

#### Performance Test Failures
- Monitor server resource usage
- Check for memory leaks
- Reduce concurrent user count for debugging

### Test Environment Setup

```bash
# Clean test environment
pkill -f uvicorn  # Kill existing servers
python test_runner.py --suite smoke  # Basic health check

# Debug specific failures
python test_host_permissions.py  # Run single suite
python -m pdb test_runner.py     # Debug with breakpoints
```

## 🔄 Activity Switching Test Scenarios

### Scenario 1: Basic Activity Switch
1. Host creates room (becomes chat)
2. Participants join
3. Host switches to snake game
4. All participants receive activity change
5. Participants can send snake game actions
6. Host switches to YouTube
7. All participants receive YouTube activity

### Scenario 2: Mid-Activity User Join
1. Room running snake game
2. New user joins during game
3. User receives current activity state
4. User can immediately participate
5. Activity continues seamlessly

### Scenario 3: Host Transfer During Activity
1. Host running YouTube activity
2. Host disconnects
3. New host is assigned
4. Activity state persists
5. New host can control activity

### Scenario 4: Rapid Activity Switching
1. Host rapidly switches: chat → snake → youtube → chat
2. All users receive all updates in order
3. No race conditions or dropped updates
4. Final state is consistent across all clients

## 📋 Test Coverage

### Current Coverage
- ✅ WebSocket connection management
- ✅ Host assignment and permissions
- ✅ Multi-room isolation
- ✅ Activity switching (mocked)
- ✅ Concurrent user actions
- ✅ Edge cases and error handling
- ✅ Performance under load

### Future Test Additions
- [ ] Browser automation tests with Playwright
- [ ] Snake game state validation
- [ ] YouTube sync accuracy tests
- [ ] Network disconnection scenarios
- [ ] Mobile client compatibility
- [ ] Real activity implementation tests

## 🎯 Test Best Practices

### Writing New Tests

```python
async def test_new_functionality():
    """Test new feature"""
    print("\n=== Test: New Functionality ===")

    # Setup phase
    client = TestClient("test_room", "test_user")
    await client.connect()

    # Action phase
    await client.send_message({"type": "new_action"})

    # Verification phase
    response = await client.wait_for_message_type("expected_response")
    assert response is not None, "Should receive response"
    assert response.get("status") == "success"

    # Cleanup phase
    await client.disconnect()

    print("✅ New functionality test passed")
```

### Test Naming Conventions
- `test_basic_*`: Core functionality tests
- `test_*_permissions`: Permission and security tests
- `test_*_scenarios`: Complex workflow tests
- `test_edge_case_*`: Edge cases and error conditions
- `test_performance_*`: Load and performance tests

### Assertion Patterns
```python
# Message validation
assert message is not None, "Should receive message"
assert message.get("type") == "expected_type"
assert message.get("data", {}).get("key") == "expected_value"

# State validation
assert client.is_host, "User should be host"
assert client.current_activity == "snake", "Activity should be snake"

# Timing validation
start_time = time.time()
# ... action ...
duration = time.time() - start_time
assert duration < 1.0, "Should complete quickly"
```

## 📞 Getting Help

### Test Failures
1. Check this guide for common solutions
2. Review server logs for errors
3. Run individual test suites to isolate issues
4. Use `--debug` flags for detailed output

### Adding New Tests
1. Follow the existing test client patterns
2. Use appropriate assertion messages
3. Include setup/cleanup phases
4. Add to test_runner.py if creating new suite

### Performance Issues
1. Check system resources during tests
2. Reduce concurrent user counts
3. Add performance profiling
4. Consider test environment limitations

---

This testing framework ensures robust, reliable activity switching functionality while maintaining good performance under realistic load conditions.