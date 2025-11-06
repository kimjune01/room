import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from main import ConnectionManager
from activities.base import ActivityType


class TestConnectionManager:
    """Test ConnectionManager functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_new_room(self, clean_manager, mock_websocket):
        """Test connecting to a new room."""
        manager = clean_manager
        room = "test_room"
        username = "test_user"

        await manager.connect(mock_websocket, room, username)

        # Check room was created
        assert room in manager.rooms
        assert mock_websocket in manager.rooms[room]

        # Check user info was stored
        assert mock_websocket in manager.client_info
        assert manager.client_info[mock_websocket]["room"] == room
        assert manager.client_info[mock_websocket]["username"] == username

        # Check host was assigned
        assert manager.room_hosts[room] == username

        # Check activity was created
        assert room in manager.room_activities

        # Verify WebSocket calls
        mock_websocket.accept.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_existing_room(self, clean_manager, mock_websockets):
        """Test connecting to an existing room."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # First user creates room
        await manager.connect(host_ws, room, "host")

        # Second user joins existing room
        await manager.connect(guest_ws, room, "guest")

        # Check both users are in room
        assert len(manager.rooms[room]) == 2
        assert host_ws in manager.rooms[room]
        assert guest_ws in manager.rooms[room]

        # Check host assignment
        assert manager.room_hosts[room] == "host"
        assert manager.is_host(host_ws) is True
        assert manager.is_host(guest_ws) is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disconnect_user(self, clean_manager, mock_websockets):
        """Test disconnecting a user."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # Connect both users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Disconnect guest
        await manager.disconnect(guest_ws)

        # Check guest was removed
        assert guest_ws not in manager.rooms[room]
        assert guest_ws not in manager.client_info

        # Check host is still there
        assert host_ws in manager.rooms[room]
        assert host_ws in manager.client_info

        # Check room still exists
        assert room in manager.rooms

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disconnect_last_user_cleans_room(self, clean_manager, mock_websocket):
        """Test that disconnecting the last user cleans up the room."""
        manager = clean_manager
        room = "test_room"

        # Connect user
        await manager.connect(mock_websocket, room, "user")

        # Verify room exists
        assert room in manager.rooms
        assert room in manager.room_hosts
        assert room in manager.room_activities

        # Disconnect user
        await manager.disconnect(mock_websocket)

        # Check room was cleaned up
        assert room not in manager.rooms
        assert room not in manager.room_hosts
        assert room not in manager.room_activities

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disconnect_host_transfers_control(self, clean_manager, mock_websockets):
        """Test that disconnecting host transfers control to another user."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # Connect both users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Disconnect host
        await manager.disconnect(host_ws)

        # Check guest became host
        assert manager.room_hosts[room] == "guest"
        assert manager.is_host(guest_ws) is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, clean_manager, mock_websockets):
        """Test broadcasting messages to room."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # Connect users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Broadcast message
        message = {"type": "test", "data": "hello"}
        await manager.broadcast_to_room(room, message)

        # Check both users received message
        host_ws.send_json.assert_called_with(message)
        guest_ws.send_json.assert_called_with(message)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_exclude_user(self, clean_manager, mock_websockets):
        """Test broadcasting with user exclusion."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # Connect users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Reset call counts
        host_ws.send_json.reset_mock()
        guest_ws.send_json.reset_mock()

        # Broadcast excluding guest
        message = {"type": "test", "data": "hello"}
        await manager.broadcast_to_room(room, message, exclude_user="guest")

        # Check only host received message
        host_ws.send_json.assert_called_once_with(message)
        guest_ws.send_json.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_to_user(self, clean_manager, mock_websockets):
        """Test sending message to specific user."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # Connect users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Reset call counts
        host_ws.send_json.reset_mock()
        guest_ws.send_json.reset_mock()

        # Send message to specific user
        message = {"type": "test", "data": "hello"}
        await manager.send_to_user(room, "guest", message)

        # Check only guest received message
        guest_ws.send_json.assert_called_once_with(message)
        host_ws.send_json.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_change_activity_host_only(self, clean_manager, mock_websockets):
        """Test that only host can change activity."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # Connect users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Host changes activity - should succeed
        success, message = await manager.change_room_activity(room, "host", ActivityType.YOUTUBE)
        assert success is True

        # Guest tries to change activity - should fail
        success, message = await manager.change_room_activity(room, "guest", ActivityType.YOUTUBE)
        assert success is False
        assert "Only the room host" in message

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_disconnected_client_in_broadcast(self, clean_manager, mock_websockets):
        """Test handling disconnected clients during broadcast."""
        manager = clean_manager
        room = "test_room"
        host_ws, guest_ws = mock_websockets['host'], mock_websockets['guest1']

        # Connect users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        # Make guest WebSocket throw exception (simulating disconnect)
        guest_ws.send_json.side_effect = Exception("Connection lost")

        # Broadcast should handle the exception and clean up
        message = {"type": "test", "data": "hello"}
        await manager.broadcast_to_room(room, message)

        # Host should still receive message
        host_ws.send_json.assert_called_with(message)

        # Guest should be cleaned up from the room
        assert guest_ws not in manager.rooms[room]

    @pytest.mark.unit
    def test_is_host_with_invalid_websocket(self, clean_manager):
        """Test is_host with WebSocket not in client_info."""
        manager = clean_manager
        fake_ws = MagicMock()

        result = manager.is_host(fake_ws)
        assert result is False