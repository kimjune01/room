import pytest
import asyncio
import time
import random
from unittest.mock import AsyncMock
from typing import List, Dict, Tuple

from main import ConnectionManager
from activities.youtube import YouTubeSyncActivity


class TestConcurrentUsers:
    """Stress tests for concurrent user scenarios."""

    @pytest.mark.stress
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_high_concurrent_connections(self):
        """Test handling many simultaneous connections."""
        manager = ConnectionManager()
        num_users = 50
        room = "stress_room"

        # Create many mock websockets
        websockets = []
        for i in range(num_users):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            ws._test_id = i  # For debugging
            websockets.append(ws)

        # Connect all users concurrently
        start_time = time.time()
        connection_tasks = []

        for i, ws in enumerate(websockets):
            task = asyncio.create_task(
                manager.connect(ws, room, f"user_{i}")
            )
            connection_tasks.append(task)

        await asyncio.gather(*connection_tasks)
        connection_time = time.time() - start_time

        # Verify all connections
        assert len(manager.rooms[room]) == num_users
        assert manager.room_hosts[room] == "user_0"

        print(f"Connected {num_users} users in {connection_time:.2f}s")

        # Test concurrent broadcasting
        start_time = time.time()
        message = {"type": "stress_test", "data": "concurrent_broadcast"}
        await manager.broadcast_to_room(room, message)
        broadcast_time = time.time() - start_time

        print(f"Broadcast to {num_users} users in {broadcast_time:.2f}s")

        # Verify all received messages
        for ws in websockets:
            ws.send_json.assert_called_with(message)

        # Test concurrent disconnections
        start_time = time.time()
        disconnect_tasks = []
        for ws in websockets:
            task = asyncio.create_task(manager.disconnect(ws))
            disconnect_tasks.append(task)

        await asyncio.gather(*disconnect_tasks)
        disconnect_time = time.time() - start_time

        print(f"Disconnected {num_users} users in {disconnect_time:.2f}s")

        # Verify cleanup
        assert room not in manager.rooms

    @pytest.mark.stress
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_rapid_room_creation_destruction(self):
        """Test rapid creation and destruction of rooms."""
        manager = ConnectionManager()
        num_rooms = 20
        users_per_room = 5

        # Create multiple rooms concurrently
        room_tasks = []
        all_websockets = []

        for room_id in range(num_rooms):
            room_name = f"room_{room_id}"
            room_websockets = []

            for user_id in range(users_per_room):
                ws = AsyncMock()
                ws.accept = AsyncMock()
                ws.send_json = AsyncMock()
                ws.close = AsyncMock()
                room_websockets.append(ws)
                all_websockets.append((ws, room_name, f"user_{user_id}"))

                # Create connection task
                task = asyncio.create_task(
                    manager.connect(ws, room_name, f"user_{user_id}")
                )
                room_tasks.append(task)

        # Execute all connections
        start_time = time.time()
        await asyncio.gather(*room_tasks)
        creation_time = time.time() - start_time

        print(f"Created {num_rooms} rooms with {users_per_room} users each in {creation_time:.2f}s")

        # Verify all rooms exist
        assert len(manager.rooms) == num_rooms
        assert len(manager.room_activities) == num_rooms

        for room_id in range(num_rooms):
            room_name = f"room_{room_id}"
            assert len(manager.rooms[room_name]) == users_per_room

        # Test concurrent broadcasting to all rooms
        start_time = time.time()
        broadcast_tasks = []
        for room_id in range(num_rooms):
            room_name = f"room_{room_id}"
            message = {"type": "room_broadcast", "room_id": room_id}
            task = asyncio.create_task(
                manager.broadcast_to_room(room_name, message)
            )
            broadcast_tasks.append(task)

        await asyncio.gather(*broadcast_tasks)
        broadcast_time = time.time() - start_time

        print(f"Broadcast to all {num_rooms} rooms in {broadcast_time:.2f}s")

        # Destroy all rooms concurrently
        start_time = time.time()
        disconnect_tasks = []
        for ws, room_name, username in all_websockets:
            task = asyncio.create_task(manager.disconnect(ws))
            disconnect_tasks.append(task)

        await asyncio.gather(*disconnect_tasks)
        destruction_time = time.time() - start_time

        print(f"Destroyed all rooms in {destruction_time:.2f}s")

        # Verify cleanup
        assert len(manager.rooms) == 0
        assert len(manager.room_activities) == 0

    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_youtube_concurrent_actions_stress(self):
        """Test YouTube activity under heavy concurrent load."""
        manager = ConnectionManager()
        room = "youtube_stress"
        num_users = 30

        # Connect users
        websockets = []
        usernames = []
        for i in range(num_users):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)
            username = f"user_{i}"
            usernames.append(username)
            await manager.connect(ws, room, username)

        activity = manager.room_activities[room]

        # First user loads video
        await activity.user_action(usernames[0], {
            "type": "activity:youtube:load_video",
            "video_id": "stress_test_video"
        })

        # Stress test: many concurrent play/pause actions
        start_time = time.time()
        action_tasks = []

        for i in range(100):  # 100 actions
            user_idx = random.randint(0, num_users - 1)
            username = usernames[user_idx]
            action_type = random.choice(["activity:youtube:play", "activity:youtube:pause"])

            task = asyncio.create_task(
                activity.user_action(username, {"type": action_type})
            )
            action_tasks.append(task)

        results = await asyncio.gather(*action_tasks, return_exceptions=True)
        action_time = time.time() - start_time

        print(f"Executed 100 concurrent YouTube actions in {action_time:.2f}s")

        # Verify no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Got {len(exceptions)} exceptions: {exceptions}"

        # Verify state consistency
        assert isinstance(activity.state["is_playing"], bool)
        assert activity.state["authoritative_user"] in usernames

        # Stress test: concurrent sync requests
        sync_tasks = []
        for username in usernames:
            task = asyncio.create_task(
                activity.user_action(username, {"type": "activity:youtube:sync_request"})
            )
            sync_tasks.append(task)

        start_time = time.time()
        sync_results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        sync_time = time.time() - start_time

        print(f"Handled {num_users} concurrent sync requests in {sync_time:.2f}s")

        # All sync requests should succeed
        sync_exceptions = [r for r in sync_results if isinstance(r, Exception)]
        assert len(sync_exceptions) == 0

        # Clean up
        await activity.stop()
        for ws in websockets:
            await manager.disconnect(ws)

    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_connection_churn_stress(self):
        """Test rapid connection and disconnection patterns."""
        manager = ConnectionManager()
        room = "churn_room"

        # Simulate connection churn over time
        active_connections = []
        total_connections = 0

        for cycle in range(10):  # 10 cycles
            # Add some users
            new_connections = []
            for i in range(5):
                ws = AsyncMock()
                ws.accept = AsyncMock()
                ws.send_json = AsyncMock()
                ws.close = AsyncMock()
                username = f"user_{total_connections}"

                await manager.connect(ws, room, username)
                new_connections.append((ws, username))
                total_connections += 1

            active_connections.extend(new_connections)

            # Remove some existing users
            if len(active_connections) > 3:
                to_remove = random.sample(active_connections, 2)
                for ws, username in to_remove:
                    await manager.disconnect(ws)
                    active_connections.remove((ws, username))

            # Broadcast a message
            if room in manager.rooms:
                message = {"type": "churn_test", "cycle": cycle}
                await manager.broadcast_to_room(room, message)

            # Small delay between cycles
            await asyncio.sleep(0.01)

        # Clean up remaining connections
        for ws, username in active_connections:
            await manager.disconnect(ws)

        # Verify final cleanup
        assert room not in manager.rooms or len(manager.rooms[room]) == 0

    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test that repeated operations don't cause memory leaks."""
        manager = ConnectionManager()

        # Run many connection/disconnection cycles
        for cycle in range(20):
            room = f"memory_test_{cycle}"
            websockets = []

            # Create connections
            for i in range(10):
                ws = AsyncMock()
                ws.accept = AsyncMock()
                ws.send_json = AsyncMock()
                ws.close = AsyncMock()
                websockets.append(ws)
                await manager.connect(ws, room, f"user_{i}")

            # Verify room created
            assert room in manager.rooms
            assert room in manager.room_activities

            # Disconnect all users
            for ws in websockets:
                await manager.disconnect(ws)

            # Verify complete cleanup
            assert room not in manager.rooms
            assert room not in manager.room_activities
            assert room not in manager.room_hosts

        # Final verification - no lingering data
        assert len(manager.rooms) == 0
        assert len(manager.room_activities) == 0
        assert len(manager.room_hosts) == 0
        assert len(manager.client_info) == 0

    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_error_resilience_under_load(self):
        """Test system resilience when errors occur under load."""
        manager = ConnectionManager()
        room = "error_resilience"

        # Mix of good and bad websockets
        good_websockets = []
        bad_websockets = []

        # Create good websockets
        for i in range(10):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            good_websockets.append(ws)
            await manager.connect(ws, room, f"good_user_{i}")

        # Create websockets that will fail during broadcast
        for i in range(5):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock(side_effect=Exception("Connection lost"))
            ws.close = AsyncMock()
            bad_websockets.append(ws)
            await manager.connect(ws, room, f"bad_user_{i}")

        assert len(manager.rooms[room]) == 15

        # Send many messages concurrently - should handle failures gracefully
        broadcast_tasks = []
        for i in range(20):
            message = {"type": "error_test", "message_id": i}
            task = asyncio.create_task(
                manager.broadcast_to_room(room, message)
            )
            broadcast_tasks.append(task)

        # Should complete without raising exceptions
        await asyncio.gather(*broadcast_tasks, return_exceptions=True)

        # Bad websockets should be cleaned up automatically
        remaining_users = len(manager.rooms[room])
        assert remaining_users <= 10  # Some or all bad websockets should be removed

        # Good websockets should still work
        test_message = {"type": "final_test"}
        await manager.broadcast_to_room(room, test_message)

        # Clean up
        for ws in good_websockets:
            if ws in manager.client_info:
                await manager.disconnect(ws)

    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """Benchmark key operations to ensure performance requirements."""
        manager = ConnectionManager()

        # Benchmark connection speed
        num_connections = 100
        websockets = []

        for i in range(num_connections):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)

        # Time connection operations
        start_time = time.time()
        for i, ws in enumerate(websockets):
            await manager.connect(ws, "benchmark_room", f"user_{i}")
        connection_time = time.time() - start_time

        print(f"Connection rate: {num_connections / connection_time:.1f} connections/second")

        # Benchmark broadcast speed
        message = {"type": "benchmark", "data": "test"}
        start_time = time.time()
        await manager.broadcast_to_room("benchmark_room", message)
        broadcast_time = time.time() - start_time

        print(f"Broadcast rate: {num_connections / broadcast_time:.1f} messages/second")

        # Benchmark disconnection speed
        start_time = time.time()
        for ws in websockets:
            await manager.disconnect(ws)
        disconnect_time = time.time() - start_time

        print(f"Disconnection rate: {num_connections / disconnect_time:.1f} disconnections/second")

        # Performance assertions (adjust thresholds as needed)
        assert connection_time < 2.0, f"Connections too slow: {connection_time}s"
        assert broadcast_time < 0.5, f"Broadcast too slow: {broadcast_time}s"
        assert disconnect_time < 2.0, f"Disconnections too slow: {disconnect_time}s"