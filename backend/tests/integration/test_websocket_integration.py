import pytest
import asyncio
import json
import websockets
from typing import Dict, List
from unittest.mock import AsyncMock

from main import app
import uvicorn
from fastapi.testclient import TestClient


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_connection_flow(self):
        """Test complete WebSocket connection and basic messaging."""
        # This test would require a running server instance
        # For now, we'll test the connection logic directly

        from main import ConnectionManager
        manager = ConnectionManager()

        # Create mock websockets
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws1.close = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock()

        room = "test_room"

        # Test connection sequence
        await manager.connect(ws1, room, "user1")
        await manager.connect(ws2, room, "user2")

        # Verify room state
        assert room in manager.rooms
        assert len(manager.rooms[room]) == 2
        assert manager.room_hosts[room] == "user1"

        # Test message broadcasting
        test_message = {"type": "test", "content": "hello"}
        await manager.broadcast_to_room(room, test_message)

        ws1.send_json.assert_called_with(test_message)
        ws2.send_json.assert_called_with(test_message)

        # Clean up
        await manager.disconnect(ws1)
        await manager.disconnect(ws2)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_room_lifecycle(self):
        """Test complete room lifecycle from creation to cleanup."""
        from main import ConnectionManager
        manager = ConnectionManager()

        # Mock websockets for multiple users
        websockets = []
        for i in range(3):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)

        room = "lifecycle_room"

        # Connect users sequentially
        await manager.connect(websockets[0], room, "host")
        await manager.connect(websockets[1], room, "guest1")
        await manager.connect(websockets[2], room, "guest2")

        # Verify room state
        assert len(manager.rooms[room]) == 3
        assert manager.room_hosts[room] == "host"
        assert room in manager.room_activities

        # Disconnect non-host users
        await manager.disconnect(websockets[1])
        assert len(manager.rooms[room]) == 2
        assert manager.room_hosts[room] == "host"  # Host should remain

        await manager.disconnect(websockets[2])
        assert len(manager.rooms[room]) == 1

        # Disconnect host (last user)
        await manager.disconnect(websockets[0])

        # Room should be completely cleaned up
        assert room not in manager.rooms
        assert room not in manager.room_hosts
        assert room not in manager.room_activities

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test handling multiple simultaneous connections."""
        from main import ConnectionManager
        manager = ConnectionManager()

        # Create multiple mock websockets
        num_users = 10
        websockets = []
        for i in range(num_users):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)

        room = "concurrent_room"

        # Connect all users concurrently
        connection_tasks = []
        for i, ws in enumerate(websockets):
            task = asyncio.create_task(
                manager.connect(ws, room, f"user{i}")
            )
            connection_tasks.append(task)

        await asyncio.gather(*connection_tasks)

        # Verify all connections
        assert len(manager.rooms[room]) == num_users
        assert manager.room_hosts[room] == "user0"  # First user is host

        # Test concurrent broadcasting
        message = {"type": "concurrent_test", "data": "broadcast"}
        await manager.broadcast_to_room(room, message)

        # Verify all websockets received the message
        for ws in websockets:
            ws.send_json.assert_called_with(message)

        # Clean up all connections concurrently
        disconnect_tasks = []
        for ws in websockets:
            task = asyncio.create_task(manager.disconnect(ws))
            disconnect_tasks.append(task)

        await asyncio.gather(*disconnect_tasks)

        # Verify cleanup
        assert room not in manager.rooms

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_activity_state_synchronization(self):
        """Test activity state sync across multiple clients."""
        from main import ConnectionManager
        from activities.youtube import YouTubeSyncActivity

        manager = ConnectionManager()

        # Create mock websockets
        host_ws = AsyncMock()
        host_ws.accept = AsyncMock()
        host_ws.send_json = AsyncMock()
        host_ws.close = AsyncMock()

        guest_ws = AsyncMock()
        guest_ws.accept = AsyncMock()
        guest_ws.send_json = AsyncMock()
        guest_ws.close = AsyncMock()

        room = "sync_room"

        # Connect users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Get the activity
        activity = manager.room_activities[room]

        # Host loads a video
        load_action = {
            "type": "activity:youtube:load_video",
            "video_id": "test123",
            "start_time": 30.0
        }

        result = await activity.user_action("host", load_action)
        assert result["type"] == "youtube_video_loaded"

        # Verify state is synchronized
        host_state = await activity.get_state_for_user("host")
        guest_state = await activity.get_state_for_user("guest")

        assert host_state["state"]["video_id"] == "test123"
        assert guest_state["state"]["video_id"] == "test123"
        assert host_state["state"]["current_time"] == 30.0
        assert guest_state["state"]["current_time"] == 30.0

        # Clean up
        await activity.stop()
        await manager.disconnect(host_ws)
        await manager.disconnect(guest_ws)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery and cleanup on connection failures."""
        from main import ConnectionManager
        manager = ConnectionManager()

        # Create websockets, one that will fail
        good_ws = AsyncMock()
        good_ws.accept = AsyncMock()
        good_ws.send_json = AsyncMock()
        good_ws.close = AsyncMock()

        failing_ws = AsyncMock()
        failing_ws.accept = AsyncMock()
        failing_ws.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        failing_ws.close = AsyncMock()

        room = "error_room"

        # Connect both users
        await manager.connect(good_ws, room, "good_user")
        await manager.connect(failing_ws, room, "failing_user")

        assert len(manager.rooms[room]) == 2

        # Try to broadcast - this should handle the failing connection
        message = {"type": "test", "data": "error_test"}
        await manager.broadcast_to_room(room, message)

        # Good websocket should receive message
        good_ws.send_json.assert_called_with(message)

        # Failing websocket should be cleaned up automatically
        assert failing_ws not in manager.rooms[room]
        assert len(manager.rooms[room]) == 1
        assert good_ws in manager.rooms[room]

        # Clean up
        await manager.disconnect(good_ws)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_host_transfer_integration(self):
        """Test complete host transfer flow."""
        from main import ConnectionManager
        manager = ConnectionManager()

        # Create mock websockets
        original_host = AsyncMock()
        original_host.accept = AsyncMock()
        original_host.send_json = AsyncMock()
        original_host.close = AsyncMock()

        new_host = AsyncMock()
        new_host.accept = AsyncMock()
        new_host.send_json = AsyncMock()
        new_host.close = AsyncMock()

        regular_user = AsyncMock()
        regular_user.accept = AsyncMock()
        regular_user.send_json = AsyncMock()
        regular_user.close = AsyncMock()

        room = "transfer_room"

        # Connect users in order
        await manager.connect(original_host, room, "original_host")
        await manager.connect(new_host, room, "new_host")
        await manager.connect(regular_user, room, "regular_user")

        # Verify initial host
        assert manager.room_hosts[room] == "original_host"
        assert manager.is_host(original_host) is True
        assert manager.is_host(new_host) is False

        # Get activity for testing permissions
        activity = manager.room_activities[room]

        # Original host should be able to change activity
        success, _ = await manager.change_room_activity(
            room, "original_host", activity.activity_type
        )
        assert success is True

        # Others should not be able to change activity
        success, message = await manager.change_room_activity(
            room, "new_host", activity.activity_type
        )
        assert success is False
        assert "Only the room host" in message

        # Remove original host
        await manager.disconnect(original_host)

        # New host should become host
        assert manager.room_hosts[room] == "new_host"
        assert manager.is_host(new_host) is True
        assert manager.is_host(regular_user) is False

        # New host should now be able to change activity
        success, _ = await manager.change_room_activity(
            room, "new_host", activity.activity_type
        )
        assert success is True

        # Clean up
        await activity.stop()
        await manager.disconnect(new_host)
        await manager.disconnect(regular_user)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_message_ordering_and_delivery(self):
        """Test that messages are delivered in correct order."""
        from main import ConnectionManager
        manager = ConnectionManager()

        # Create websockets with message tracking
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()
        ws1_messages = []
        ws1.send_json = AsyncMock(side_effect=lambda msg: ws1_messages.append(msg))

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()
        ws2_messages = []
        ws2.send_json = AsyncMock(side_effect=lambda msg: ws2_messages.append(msg))

        room = "ordering_room"

        # Connect users
        await manager.connect(ws1, room, "user1")
        await manager.connect(ws2, room, "user2")

        # Send multiple messages in sequence
        messages = [
            {"type": "msg1", "sequence": 1},
            {"type": "msg2", "sequence": 2},
            {"type": "msg3", "sequence": 3}
        ]

        for msg in messages:
            await manager.broadcast_to_room(room, msg)

        # Verify both users received all messages in order
        assert len(ws1_messages) == 3
        assert len(ws2_messages) == 3

        for i, expected_msg in enumerate(messages):
            assert ws1_messages[i]["sequence"] == expected_msg["sequence"]
            assert ws2_messages[i]["sequence"] == expected_msg["sequence"]

        # Test targeted messaging
        ws1_messages.clear()
        ws2_messages.clear()

        target_msg = {"type": "targeted", "content": "private"}
        await manager.send_to_user(room, "user1", target_msg)

        # Only user1 should receive the message
        assert len(ws1_messages) == 1
        assert len(ws2_messages) == 0
        assert ws1_messages[0] == target_msg

        # Clean up
        await manager.disconnect(ws1)
        await manager.disconnect(ws2)