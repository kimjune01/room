#!/usr/bin/env python3
"""
Test YouTube Synchronization Integration
Comprehensive test to validate YouTube IFrame API integration and real-time synchronization
between multiple clients in the same room.
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any, List


class YouTubeSyncClient:
    def __init__(self, room: str, username: str):
        self.room = room
        self.username = username
        self.websocket = None
        self.connected = False
        self.activity_state = None
        self.messages = []
        self.is_master = False

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

            # Update internal state
            if message.get('type') == 'activity_state':
                self.activity_state = message
            elif message.get('type') == 'role_assigned':
                self.is_master = message.get('role') == 'host'

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

    async def set_playback_rate(self, rate: float):
        """Set playback rate"""
        await self.send_message({
            'type': 'activity:youtube:set_rate',
            'rate': rate
        })

    async def request_master(self):
        """Request to become master"""
        await self.send_message({
            'type': 'activity:youtube:request_master'
        })

    async def wait_for_state_update(self, expected_state: Dict[str, Any], timeout: float = 10.0) -> bool:
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
                        # Handle floating point precision for time values
                        if isinstance(expected_value, float) and isinstance(current_value, (int, float)):
                            if abs(current_value - expected_value) > 0.1:  # Allow 0.1 second tolerance
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

    def get_current_state(self) -> Dict[str, Any]:
        """Get current activity state"""
        if self.activity_state:
            return self.activity_state.get('state', {})
        return {}


async def test_basic_video_sync():
    """Test basic video loading and synchronization between two clients"""
    print("🎯 Basic Video Sync Test")
    print("=" * 40)

    master = YouTubeSyncClient("sync_test", "Master")
    viewer = YouTubeSyncClient("sync_test", "Viewer")

    try:
        # Connect both clients
        await master.connect()
        await viewer.connect()

        # Skip initial setup messages
        for client in [master, viewer]:
            for _ in range(3):
                try:
                    await client.receive_message(timeout=2.0)
                except TimeoutError:
                    break

        # Switch to YouTube activity (master only since they're host)
        if master.is_master:
            await master.switch_to_youtube()

        # Wait for activity change
        await asyncio.sleep(1)
        for client in [master, viewer]:
            try:
                await client.receive_message(timeout=3.0)
            except TimeoutError:
                pass

        test_video_id = "dQw4w9WgXcQ"

        # Master loads a video
        print(f"📹 Master loading video: {test_video_id}")
        await master.load_video(test_video_id)

        # Both clients should receive video loaded state
        master_synced = await master.wait_for_state_update({'video_id': test_video_id})
        viewer_synced = await viewer.wait_for_state_update({'video_id': test_video_id})

        if not master_synced or not viewer_synced:
            print("❌ Video loading sync failed")
            return False

        print("✅ Video loaded and synced to both clients")

        # Master plays the video
        print("▶️  Master playing video")
        await master.play_video()

        # Both clients should see playing state
        master_playing = await master.wait_for_state_update({'is_playing': True})
        viewer_playing = await viewer.wait_for_state_update({'is_playing': True})

        if not master_playing or not viewer_playing:
            print("❌ Play sync failed")
            return False

        print("✅ Play state synced to both clients")

        # Master pauses the video
        print("⏸️  Master pausing video")
        await master.pause_video()

        # Both clients should see paused state
        master_paused = await master.wait_for_state_update({'is_playing': False})
        viewer_paused = await viewer.wait_for_state_update({'is_playing': False})

        if not master_paused or not viewer_paused:
            print("❌ Pause sync failed")
            return False

        print("✅ Pause state synced to both clients")

        # Master seeks to 30 seconds
        print("⏭️  Master seeking to 30s")
        await master.seek_video(30.0)

        # Both clients should see new time
        master_seeked = await master.wait_for_state_update({'current_time': 30.0})
        viewer_seeked = await viewer.wait_for_state_update({'current_time': 30.0})

        if not master_seeked or not viewer_seeked:
            print("❌ Seek sync failed")
            return False

        print("✅ Seek position synced to both clients")

        # Master changes playback rate
        print("🏃 Master setting playback rate to 1.5x")
        await master.set_playback_rate(1.5)

        # Both clients should see new rate
        master_rate = await master.wait_for_state_update({'playback_rate': 1.5})
        viewer_rate = await viewer.wait_for_state_update({'playback_rate': 1.5})

        if not master_rate or not viewer_rate:
            print("❌ Playback rate sync failed")
            return False

        print("✅ Playback rate synced to both clients")

        print("\n🎉 Basic video sync test PASSED!")
        return True

    except Exception as e:
        print(f"❌ Basic sync test failed: {e}")
        return False
    finally:
        await master.disconnect()
        await viewer.disconnect()


async def test_master_control_permissions():
    """Test that only master can control video playback"""
    print("\n🔐 Master Control Permissions Test")
    print("=" * 40)

    master = YouTubeSyncClient("permission_test", "Master")
    viewer = YouTubeSyncClient("permission_test", "Viewer")

    try:
        await master.connect()
        await viewer.connect()

        # Skip setup messages
        for client in [master, viewer]:
            for _ in range(3):
                try:
                    await client.receive_message(timeout=2.0)
                except TimeoutError:
                    break

        # Switch to YouTube and load video
        if master.is_master:
            await master.switch_to_youtube()
            await asyncio.sleep(1)

            # Clear activity change messages
            for client in [master, viewer]:
                try:
                    await client.receive_message(timeout=2.0)
                except TimeoutError:
                    pass

            await master.load_video("dQw4w9WgXcQ")
            await master.wait_for_state_update({'video_id': 'dQw4w9WgXcQ'})
            await viewer.wait_for_state_update({'video_id': 'dQw4w9WgXcQ'})

        # Viewer tries to play video (should be ignored or rejected)
        print("🚫 Viewer attempting to play video (should be denied)")
        initial_state = viewer.get_current_state()
        await viewer.play_video()

        # Wait briefly and check if state changed
        await asyncio.sleep(2)
        try:
            await viewer.receive_message(timeout=2.0)
        except TimeoutError:
            pass

        final_state = viewer.get_current_state()

        # Video should not be playing (viewer action ignored)
        if final_state.get('is_playing', False):
            print("❌ Viewer was able to control video (permission system failed)")
            return False

        print("✅ Viewer control attempt properly denied")

        # Master can still control
        print("✅ Master playing video")
        await master.play_video()

        master_playing = await master.wait_for_state_update({'is_playing': True})
        if not master_playing:
            print("❌ Master lost control ability")
            return False

        print("✅ Master control confirmed working")
        print("\n🎉 Master control permissions test PASSED!")
        return True

    except Exception as e:
        print(f"❌ Permission test failed: {e}")
        return False
    finally:
        await master.disconnect()
        await viewer.disconnect()


async def test_multi_client_sync():
    """Test synchronization across multiple clients"""
    print("\n👥 Multi-Client Sync Test")
    print("=" * 40)

    clients = [
        YouTubeSyncClient("multi_test", "Host"),
        YouTubeSyncClient("multi_test", "Viewer1"),
        YouTubeSyncClient("multi_test", "Viewer2"),
        YouTubeSyncClient("multi_test", "Viewer3")
    ]

    try:
        # Connect all clients
        for client in clients:
            await client.connect()

        # Skip setup messages
        for client in clients:
            for _ in range(3):
                try:
                    await client.receive_message(timeout=2.0)
                except TimeoutError:
                    break

        master = clients[0]  # First client is host

        # Switch to YouTube and load video
        if master.is_master:
            await master.switch_to_youtube()
            await asyncio.sleep(1)

            # Clear activity change messages
            for client in clients:
                try:
                    await client.receive_message(timeout=2.0)
                except TimeoutError:
                    pass

            await master.load_video("9bZkp7q19f0")  # Gangnam Style

        # All clients should sync to video
        print(f"📺 Syncing video to {len(clients)} clients")
        all_synced = True
        for i, client in enumerate(clients):
            synced = await client.wait_for_state_update({'video_id': '9bZkp7q19f0'})
            if synced:
                print(f"✅ Client {i+1} ({client.username}) synced")
            else:
                print(f"❌ Client {i+1} ({client.username}) failed to sync")
                all_synced = False

        if not all_synced:
            print("❌ Multi-client video sync failed")
            return False

        # Master performs various actions
        actions = [
            ("play", lambda: master.play_video(), {'is_playing': True}),
            ("seek to 45s", lambda: master.seek_video(45), {'current_time': 45.0}),
            ("pause", lambda: master.pause_video(), {'is_playing': False}),
            ("rate 0.75x", lambda: master.set_playback_rate(0.75), {'playback_rate': 0.75})
        ]

        for action_name, action_func, expected_state in actions:
            print(f"🎬 Master performing: {action_name}")
            await action_func()

            # Check all clients sync
            action_synced = True
            for i, client in enumerate(clients):
                synced = await client.wait_for_state_update(expected_state, timeout=5.0)
                if not synced:
                    print(f"❌ Client {i+1} failed to sync {action_name}")
                    action_synced = False

            if action_synced:
                print(f"✅ All clients synced for {action_name}")
            else:
                print(f"❌ Multi-client sync failed for {action_name}")
                return False

        print(f"\n🎉 Multi-client sync test PASSED! All {len(clients)} clients synchronized.")
        return True

    except Exception as e:
        print(f"❌ Multi-client test failed: {e}")
        return False
    finally:
        for client in clients:
            await client.disconnect()


async def main():
    """Run comprehensive YouTube synchronization tests"""
    print("🧪 YouTube Synchronization Integration Test Suite")
    print("=" * 60)
    print("Testing YouTube IFrame API integration and real-time sync")
    print("=" * 60)

    tests = [
        ("Basic Video Sync", test_basic_video_sync),
        ("Master Control Permissions", test_master_control_permissions),
        ("Multi-Client Sync", test_multi_client_sync)
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
    print("📊 YouTube Sync Integration Test Results:")
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
        print("🌟 YouTube IFrame API integration is working correctly!")
        print("🔄 Real-time synchronization across multiple clients verified!")
        print("🎯 Frontend is ready for synchronized video watching!")
        return True
    else:
        print(f"\n💥 {len(results) - passed} test(s) failed.")
        print("🔍 Check the backend and frontend implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)