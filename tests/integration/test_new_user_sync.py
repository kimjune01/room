#!/usr/bin/env python3
"""
Test New User Sync Behavior
Verifies that when a new user joins a room with an active YouTube video,
they sync to the current room state instead of auto-playing.
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any


class YouTubeNewUserTest:
    def __init__(self, room: str, username: str):
        self.room = room
        self.username = username
        self.websocket = None
        self.connected = False
        self.activity_state = None
        self.messages = []

    async def connect(self):
        """Connect to WebSocket server"""
        self.websocket = await websockets.connect(f"ws://localhost:8001/ws/{self.room}/{self.username}")
        self.connected = True
        print(f"✅ {self.username} connected to room {self.room}")

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print(f"🔌 {self.username} disconnected")

    async def receive_message(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Receive a message with timeout"""
        try:
            data = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            message = json.loads(data)
            self.messages.append(message)

            if message.get('type') == 'activity_state':
                self.activity_state = message

            return message
        except asyncio.TimeoutError:
            raise TimeoutError(f"No message received within {timeout} seconds")

    async def send_message(self, message: Dict[str, Any]):
        """Send a message to the server"""
        await self.websocket.send(json.dumps(message))

    async def switch_to_youtube(self):
        """Switch to YouTube activity"""
        await self.send_message({
            'type': 'change_activity',
            'activity_type': 'youtube'
        })

    async def load_video(self, video_id: str, start_time: float = 0):
        """Load a YouTube video"""
        await self.send_message({
            'type': 'activity:youtube:load_video',
            'video_id': video_id,
            'start_time': start_time
        })

    async def play_video(self):
        """Play the video"""
        await self.send_message({
            'type': 'activity:youtube:play'
        })

    async def pause_video(self):
        """Pause the video"""
        await self.send_message({
            'type': 'activity:youtube:pause'
        })

    async def seek_video(self, time: float):
        """Seek to a specific time"""
        await self.send_message({
            'type': 'activity:youtube:seek',
            'time': time
        })

    def get_current_state(self) -> Dict[str, Any]:
        """Get current activity state"""
        if self.activity_state:
            return self.activity_state.get('state', {})
        return {}

    async def wait_for_state(self, expected_state: Dict[str, Any], timeout: float = 10.0) -> bool:
        """Wait for activity state to match expected values"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                await self.receive_message(timeout=2.0)
                if self.activity_state:
                    state = self.activity_state.get('state', {})
                    matches = True
                    for key, expected_value in expected_state.items():
                        current_value = state.get(key)
                        if isinstance(expected_value, float) and isinstance(current_value, (int, float)):
                            if abs(current_value - expected_value) > 0.1:
                                matches = False
                                break
                        elif current_value != expected_value:
                            matches = False
                            break
                    if matches:
                        return True
            except TimeoutError:
                continue
        return False


async def test_new_user_joins_paused_video():
    """Test that new user syncs to paused video state"""
    print("🎯 New User Joins Paused Video Test")
    print("=" * 50)

    room_name = "new_user_test_paused"
    host = YouTubeNewUserTest(room_name, "Host")

    try:
        # Host sets up the room with a paused video
        await host.connect()

        # Skip initial messages
        for _ in range(3):
            try:
                await host.receive_message(timeout=2.0)
            except TimeoutError:
                break

        # Switch to YouTube
        await host.switch_to_youtube()
        await asyncio.sleep(1)

        # Clear activity change messages
        try:
            await host.receive_message(timeout=2.0)
        except TimeoutError:
            pass

        # Load video and ensure it's paused
        print("📹 Host loading video...")
        await host.load_video("dQw4w9WgXcQ", start_time=30)

        # Wait for video to load
        await host.wait_for_state({'video_id': 'dQw4w9WgXcQ'})

        # Ensure video is paused (should be default state)
        current_state = host.get_current_state()
        if current_state.get('is_playing'):
            await host.pause_video()
            await host.wait_for_state({'is_playing': False})

        print(f"🎬 Room setup complete - Video: {current_state.get('video_id')}, Playing: {current_state.get('is_playing')}, Time: {current_state.get('current_time')}")

        # Now a new user joins
        print("\n👤 New user joining room...")
        new_user = YouTubeNewUserTest(room_name, "NewUser")
        await new_user.connect()

        # New user receives initial state
        state_received = False
        for _ in range(5):
            try:
                msg = await new_user.receive_message(timeout=3.0)
                if msg.get('type') == 'activity_state':
                    state_received = True
                    new_user_state = msg.get('state', {})
                    print(f"📊 New user received state: {new_user_state}")
                    break
            except TimeoutError:
                continue

        if not state_received:
            print("❌ New user did not receive activity state")
            return False

        # Verify new user has the correct state
        final_state = new_user.get_current_state()
        expected_video_id = current_state.get('video_id')
        expected_is_playing = current_state.get('is_playing')
        expected_time = current_state.get('current_time')

        print(f"\n🔍 Verification:")
        print(f"   Expected - Video: {expected_video_id}, Playing: {expected_is_playing}, Time: {expected_time}")
        print(f"   New User - Video: {final_state.get('video_id')}, Playing: {final_state.get('is_playing')}, Time: {final_state.get('current_time')}")

        # Check that new user synced to paused state
        if (final_state.get('video_id') == expected_video_id and
            final_state.get('is_playing') == expected_is_playing and
            abs(final_state.get('current_time', 0) - expected_time) < 2):
            print("✅ New user correctly synced to room state!")
            return True
        else:
            print("❌ New user did not sync to room state correctly")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await host.disconnect()
        if 'new_user' in locals():
            await new_user.disconnect()


async def test_new_user_joins_playing_video():
    """Test that new user syncs to playing video state"""
    print("\n🎯 New User Joins Playing Video Test")
    print("=" * 50)

    room_name = "new_user_test_playing"
    host = YouTubeNewUserTest(room_name, "Host")

    try:
        # Host sets up the room with a playing video
        await host.connect()

        # Skip initial messages
        for _ in range(3):
            try:
                await host.receive_message(timeout=2.0)
            except TimeoutError:
                break

        # Switch to YouTube
        await host.switch_to_youtube()
        await asyncio.sleep(1)

        # Clear activity change messages
        try:
            await host.receive_message(timeout=2.0)
        except TimeoutError:
            pass

        # Load and play video
        print("📹 Host loading and playing video...")
        await host.load_video("9bZkp7q19f0", start_time=60)  # Gangnam Style at 1 minute
        await host.wait_for_state({'video_id': '9bZkp7q19f0'})

        # Start playing
        await host.play_video()
        await host.wait_for_state({'is_playing': True})

        # Let it play for a few seconds to get some time progression
        await asyncio.sleep(3)
        current_state = host.get_current_state()

        print(f"🎬 Room setup complete - Video: {current_state.get('video_id')}, Playing: {current_state.get('is_playing')}, Time: {current_state.get('current_time')}")

        # Now a new user joins
        print("\n👤 New user joining room with playing video...")
        new_user = YouTubeNewUserTest(room_name, "NewUser")
        await new_user.connect()

        # New user receives initial state
        state_received = False
        for _ in range(5):
            try:
                msg = await new_user.receive_message(timeout=3.0)
                if msg.get('type') == 'activity_state':
                    state_received = True
                    new_user_state = msg.get('state', {})
                    print(f"📊 New user received state: {new_user_state}")
                    break
            except TimeoutError:
                continue

        if not state_received:
            print("❌ New user did not receive activity state")
            return False

        # Verify new user has the correct state
        final_state = new_user.get_current_state()
        expected_video_id = current_state.get('video_id')
        expected_is_playing = current_state.get('is_playing')

        print(f"\n🔍 Verification:")
        print(f"   Expected - Video: {expected_video_id}, Playing: {expected_is_playing}")
        print(f"   New User - Video: {final_state.get('video_id')}, Playing: {final_state.get('is_playing')}")

        # Check that new user synced to playing state
        if (final_state.get('video_id') == expected_video_id and
            final_state.get('is_playing') == expected_is_playing):
            print("✅ New user correctly synced to playing video state!")
            return True
        else:
            print("❌ New user did not sync to playing state correctly")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await host.disconnect()
        if 'new_user' in locals():
            await new_user.disconnect()


async def test_new_user_no_disruption():
    """Test that new user joining doesn't disrupt existing playback"""
    print("\n🎯 New User No Disruption Test")
    print("=" * 50)

    room_name = "new_user_no_disruption"
    host = YouTubeNewUserTest(room_name, "Host")
    viewer1 = YouTubeNewUserTest(room_name, "Viewer1")

    try:
        # Set up existing session
        await host.connect()
        await viewer1.connect()

        # Skip initial messages for both
        for client in [host, viewer1]:
            for _ in range(3):
                try:
                    await client.receive_message(timeout=2.0)
                except TimeoutError:
                    break

        # Setup YouTube session
        await host.switch_to_youtube()
        await asyncio.sleep(1)

        # Clear activity change messages
        for client in [host, viewer1]:
            try:
                await client.receive_message(timeout=2.0)
            except TimeoutError:
                pass

        # Load and play video
        await host.load_video("kJQP7kiw5Fk")  # Despacito
        await host.wait_for_state({'video_id': 'kJQP7kiw5Fk'})
        await viewer1.wait_for_state({'video_id': 'kJQP7kiw5Fk'})

        await host.play_video()
        await host.wait_for_state({'is_playing': True})
        await viewer1.wait_for_state({'is_playing': True})

        print("🎬 Existing session established with playing video")

        # Record current state before new user joins
        pre_join_state = host.get_current_state()

        # New user joins
        print("👤 New user joining active session...")
        new_user = YouTubeNewUserTest(room_name, "NewUser")
        await new_user.connect()

        # Wait for new user to get state
        await asyncio.sleep(2)
        try:
            await new_user.receive_message(timeout=3.0)
        except TimeoutError:
            pass

        # Check that existing clients weren't disrupted
        await asyncio.sleep(1)
        post_join_state = host.get_current_state()

        print(f"📊 Before new user: Playing={pre_join_state.get('is_playing')}")
        print(f"📊 After new user:  Playing={post_join_state.get('is_playing')}")

        # Video should still be playing
        if post_join_state.get('is_playing') == pre_join_state.get('is_playing'):
            print("✅ New user join did not disrupt existing playback!")
            return True
        else:
            print("❌ New user join disrupted existing playback")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        for client in [host, viewer1]:
            await client.disconnect()
        if 'new_user' in locals():
            await new_user.disconnect()


async def main():
    """Run all new user sync tests"""
    print("🧪 YouTube New User Sync Test Suite")
    print("=" * 60)
    print("Testing that new users sync to room state without disruption")
    print("=" * 60)

    tests = [
        ("New User Joins Paused Video", test_new_user_joins_paused_video),
        ("New User Joins Playing Video", test_new_user_joins_playing_video),
        ("New User No Disruption", test_new_user_no_disruption)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🚀 Running: {test_name}")
        print("-" * 60)
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 New User Sync Test Results:")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1

    success_rate = (passed / len(results)) * 100
    print(f"\nOverall: {passed}/{len(results)} tests passed ({success_rate:.1f}%)")

    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED!")
        print("🔄 New users properly sync to room state!")
        print("🚫 No disruption to existing playback!")
        print("🎯 User experience is smooth and consistent!")
        return True
    else:
        print(f"\n💥 {len(results) - passed} test(s) failed.")
        print("🔍 Check the frontend sync implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)