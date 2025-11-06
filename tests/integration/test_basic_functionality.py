#!/usr/bin/env python3
"""
Consolidated Test Suite for Room Activities System
Combines essential tests into a single maintainable file
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any


class TestClient:
    """Simplified test client for WebSocket connections"""

    def __init__(self, room: str, username: str):
        self.room = room
        self.username = username
        self.websocket = None
        self.activity_state = None

    async def connect(self):
        self.websocket = await websockets.connect(f"ws://localhost:8001/ws/{self.room}/{self.username}")
        print(f"✅ {self.username} connected to {self.room}")

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            print(f"🔌 {self.username} disconnected")

    async def send(self, message: Dict[str, Any]):
        await self.websocket.send(json.dumps(message))

    async def receive(self, timeout: float = 5.0) -> Dict[str, Any]:
        data = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
        msg = json.loads(data)
        if msg.get('type') == 'activity_state':
            self.activity_state = msg
        return msg

    async def skip_setup_messages(self):
        """Skip initial connection messages and get activity state"""
        for _ in range(5):
            try:
                msg = await self.receive(timeout=2.0)
                # Keep processing until we get activity state or timeout
                if msg.get('type') == 'activity_state':
                    break
            except asyncio.TimeoutError:
                break

    async def switch_activity(self, activity_type: str):
        """Switch to specified activity"""
        await self.send({'type': 'change_activity', 'activity_type': activity_type})
        await self.receive(timeout=3.0)  # Activity change confirmation

    def get_state(self) -> Dict[str, Any]:
        """Get current activity state"""
        return self.activity_state.get('state', {}) if self.activity_state else {}


async def test_basic_connection():
    """Test basic WebSocket connection and room joining"""
    print("🔗 Testing Basic Connection")

    client = TestClient("test_room", "TestUser")

    try:
        await client.connect()
        await client.skip_setup_messages()

        # Verify we have some state
        state = client.get_state()
        assert 'video_id' in state or 'board' in state, "Should have activity state"

        print("✅ Basic connection test passed")
        return True
    except Exception as e:
        print(f"❌ Basic connection test failed: {e}")
        return False
    finally:
        await client.disconnect()


async def test_host_permissions():
    """Test that host has special permissions"""
    print("👑 Testing Host Permissions")

    host = TestClient("host_test", "Host")
    viewer = TestClient("host_test", "Viewer")

    try:
        await host.connect()
        await viewer.connect()

        await host.skip_setup_messages()
        await viewer.skip_setup_messages()

        # Host can change activity
        await host.switch_activity('youtube')
        await asyncio.sleep(1)

        # Both should receive activity change
        await host.receive(timeout=3.0)
        await viewer.receive(timeout=3.0)

        # Verify both are on YouTube
        host_state = host.get_state()
        viewer_state = viewer.get_state()

        assert 'video_id' in host_state, "Host should have YouTube state"
        assert 'video_id' in viewer_state, "Viewer should have YouTube state"

        print("✅ Host permissions test passed")
        return True
    except Exception as e:
        print(f"❌ Host permissions test failed: {e}")
        return False
    finally:
        await host.disconnect()
        await viewer.disconnect()


async def test_youtube_sync():
    """Test YouTube video synchronization"""
    print("📺 Testing YouTube Sync")

    master = TestClient("youtube_sync", "Master")
    viewer = TestClient("youtube_sync", "Viewer")

    try:
        await master.connect()
        await viewer.connect()

        await master.skip_setup_messages()
        await viewer.skip_setup_messages()

        # Switch to YouTube
        await master.switch_activity('youtube')
        await asyncio.sleep(1)

        # Clear activity change messages
        await master.receive(timeout=2.0)
        await viewer.receive(timeout=2.0)

        # Master loads video
        await master.send({
            'type': 'activity:youtube:load_video',
            'video_id': 'dQw4w9WgXcQ',
            'start_time': 0
        })

        # Both should receive video loaded
        await master.receive(timeout=3.0)
        await viewer.receive(timeout=3.0)

        # Check states
        master_state = master.get_state()
        viewer_state = viewer.get_state()

        assert master_state.get('video_id') == 'dQw4w9WgXcQ', "Master should have video"
        assert viewer_state.get('video_id') == 'dQw4w9WgXcQ', "Viewer should have video"

        # Test play sync
        await master.send({'type': 'activity:youtube:play'})

        # Both should get play state
        await master.receive(timeout=3.0)
        await viewer.receive(timeout=3.0)

        master_state = master.get_state()
        viewer_state = viewer.get_state()

        assert master_state.get('is_playing') == True, "Master should be playing"
        assert viewer_state.get('is_playing') == True, "Viewer should be playing"

        print("✅ YouTube sync test passed")
        return True
    except Exception as e:
        print(f"❌ YouTube sync test failed: {e}")
        return False
    finally:
        await master.disconnect()
        await viewer.disconnect()


async def test_snake_game():
    """Test Snake game basic functionality"""
    print("🐍 Testing Snake Game")

    player = TestClient("snake_game", "Player")

    try:
        await player.connect()
        await player.skip_setup_messages()

        # Should start with Snake (default activity)
        state = player.get_state()
        assert 'board' in state, "Should have Snake game state"

        # Join game
        await player.send({'type': 'activity:snake:join'})
        await player.receive(timeout=3.0)

        # Check joined state
        state = player.get_state()
        assert 'Player' in state.get('players', {}), "Player should be in game"

        print("✅ Snake game test passed")
        return True
    except Exception as e:
        print(f"❌ Snake game test failed: {e}")
        return False
    finally:
        await player.disconnect()


async def test_new_user_sync():
    """Test that new users sync to existing room state"""
    print("👤 Testing New User Sync")

    host = TestClient("new_user_sync", "Host")

    try:
        # Setup room with specific state
        await host.connect()
        await host.skip_setup_messages()

        await host.switch_activity('youtube')
        await asyncio.sleep(1)
        await host.receive(timeout=2.0)

        # Load and pause video
        await host.send({
            'type': 'activity:youtube:load_video',
            'video_id': 'test123',
            'start_time': 30
        })
        await host.receive(timeout=3.0)

        current_state = host.get_state()

        # New user joins
        new_user = TestClient("new_user_sync", "NewUser")
        await new_user.connect()
        await new_user.skip_setup_messages()

        # New user should get same state
        new_state = new_user.get_state()

        assert new_state.get('video_id') == current_state.get('video_id'), "Video should match"
        assert new_state.get('current_time') == current_state.get('current_time'), "Time should match"

        print("✅ New user sync test passed")
        return True
    except Exception as e:
        print(f"❌ New user sync test failed: {e}")
        return False
    finally:
        await host.disconnect()
        if 'new_user' in locals():
            await new_user.disconnect()


async def run_test_suite():
    """Run all tests in the consolidated suite"""
    print("🧪 Room Activities System Test Suite")
    print("=" * 50)

    tests = [
        ("Basic Connection", test_basic_connection),
        ("Host Permissions", test_host_permissions),
        ("YouTube Sync", test_youtube_sync),
        ("Snake Game", test_snake_game),
        ("New User Sync", test_new_user_sync),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n🚀 Running: {name}")
        print("-" * 30)

        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                print(f"❌ {name} failed")
        except Exception as e:
            print(f"💥 {name} error: {e}")

    print(f"\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! System is working correctly.")
        return True
    else:
        print(f"💥 {total - passed} test(s) failed.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test_suite())
    exit(0 if success else 1)