import pytest
import asyncio
import time
from unittest.mock import AsyncMock
from typing import Dict, List

from main import ConnectionManager
from activities.youtube import YouTubeSyncActivity
from activities.base import ActivityType


class TestYouTubeIntegration:
    """Integration tests for YouTube activity with real WebSocket simulation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_youtube_session_flow(self):
        """Test complete YouTube session from start to finish."""
        manager = ConnectionManager()

        # Create mock websockets for multiple users
        host_ws = AsyncMock()
        host_ws.accept = AsyncMock()
        host_ws.send_json = AsyncMock()
        host_ws.close = AsyncMock()

        guest1_ws = AsyncMock()
        guest1_ws.accept = AsyncMock()
        guest1_ws.send_json = AsyncMock()
        guest1_ws.close = AsyncMock()

        guest2_ws = AsyncMock()
        guest2_ws.accept = AsyncMock()
        guest2_ws.send_json = AsyncMock()
        guest2_ws.close = AsyncMock()

        room = "youtube_session"

        # Users join room
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest1_ws, room, "guest1")
        await manager.connect(guest2_ws, room, "guest2")

        activity = manager.room_activities[room]

        # 1. Host loads video
        load_result = await activity.user_action("host", {
            "type": "activity:youtube:load_video",
            "video_id": "dQw4w9WgXcQ",
            "start_time": 0.0
        })

        assert load_result["type"] == "youtube_video_loaded"
        assert activity.state["video_id"] == "dQw4w9WgXcQ"
        assert activity.state["master_user"] == "host"

        # 2. Guest1 starts playback (democratic control)
        play_result = await activity.user_action("guest1", {
            "type": "activity:youtube:play"
        })

        assert play_result["type"] == "youtube_play"
        assert activity.state["is_playing"] is True
        assert activity.state["authoritative_user"] == "guest1"

        # 3. Guest2 pauses (anyone can pause)
        pause_result = await activity.user_action("guest2", {
            "type": "activity:youtube:pause"
        })

        assert pause_result["type"] == "youtube_pause"
        assert activity.state["is_playing"] is False
        assert activity.state["authoritative_user"] == "guest2"

        # 4. Host seeks (only master can seek)
        seek_result = await activity.user_action("host", {
            "type": "activity:youtube:seek",
            "time": 60.0
        })

        assert seek_result["type"] == "youtube_seek"
        assert activity.state["current_time"] == 60.0

        # 5. Guest tries to seek (should fail)
        seek_fail_result = await activity.user_action("guest1", {
            "type": "activity:youtube:seek",
            "time": 30.0
        })

        assert seek_fail_result["type"] == "error"
        assert "Only the master user" in seek_fail_result["message"]
        assert activity.state["current_time"] == 60.0  # Should not change

        # 6. Host changes playback rate
        rate_result = await activity.user_action("host", {
            "type": "activity:youtube:set_rate",
            "rate": 1.5
        })

        assert rate_result["type"] == "youtube_rate_changed"
        assert activity.state["playback_rate"] == 1.5

        # Clean up
        await activity.stop()
        await manager.disconnect(host_ws)
        await manager.disconnect(guest1_ws)
        await manager.disconnect(guest2_ws)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_buffering_coordination(self):
        """Test buffering coordination across multiple clients."""
        manager = ConnectionManager()

        # Create websockets with message tracking
        users = {}
        for i, username in enumerate(["host", "guest1", "guest2"]):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.sent_messages = []
            ws.send_json = AsyncMock(side_effect=lambda msg, u=username: users[u]['ws'].sent_messages.append(msg))
            users[username] = {"ws": ws, "messages": ws.sent_messages}

        room = "buffering_room"

        # Connect all users
        for username in users:
            await manager.connect(users[username]["ws"], room, username)

        activity = manager.room_activities[room]

        # Load video and start playing
        await activity.user_action("host", {
            "type": "activity:youtube:load_video",
            "video_id": "test123"
        })

        await activity.user_action("host", {
            "type": "activity:youtube:play"
        })

        assert activity.state["is_playing"] is True

        # Guest1 starts buffering
        buffer_start = await activity.user_action("guest1", {
            "type": "activity:youtube:buffer_start"
        })

        assert buffer_start["type"] == "youtube_buffer_start"
        assert "guest1" in activity.state["buffering_users"]
        assert activity.state["is_playing"] is False  # Should auto-pause

        # Guest2 also starts buffering
        await activity.user_action("guest2", {
            "type": "activity:youtube:buffer_start"
        })

        assert len(activity.state["buffering_users"]) == 2
        assert activity.state["is_playing"] is False

        # Guest1 finishes buffering
        buffer_end = await activity.user_action("guest1", {
            "type": "activity:youtube:buffer_end"
        })

        assert buffer_end["type"] == "youtube_buffer_end"
        assert "guest1" not in activity.state["buffering_users"]
        assert len(activity.state["buffering_users"]) == 1
        assert activity.state["is_playing"] is False  # Should stay paused until all finish

        # Guest2 finishes buffering
        await activity.user_action("guest2", {
            "type": "activity:youtube:buffer_end"
        })

        assert len(activity.state["buffering_users"]) == 0

        # Clean up
        await activity.stop()
        for username in users:
            await manager.disconnect(users[username]["ws"])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_master_control_transfer_scenario(self):
        """Test master control transfer in various scenarios."""
        manager = ConnectionManager()

        # Create websockets
        host_ws = AsyncMock()
        host_ws.accept = AsyncMock()
        host_ws.send_json = AsyncMock()
        host_ws.close = AsyncMock()

        guest_ws = AsyncMock()
        guest_ws.accept = AsyncMock()
        guest_ws.send_json = AsyncMock()
        guest_ws.close = AsyncMock()

        room = "master_transfer"

        # Connect users
        await manager.connect(host_ws, room, "host")
        await manager.connect(guest_ws, room, "guest")

        activity = manager.room_activities[room]

        # Host loads video (becomes master automatically)
        await activity.user_action("host", {
            "type": "activity:youtube:load_video",
            "video_id": "test123"
        })

        assert activity.state["master_user"] == "host"

        # Guest requests master control (should fail - host is still present)
        request_result = await activity.user_action("guest", {
            "type": "activity:youtube:request_master"
        })

        assert request_result["type"] == "error"
        assert "Master control is held by" in request_result["message"]
        assert activity.state["master_user"] == "host"

        # Host disconnects
        await manager.disconnect(host_ws)

        # Guest should automatically become master
        assert activity.state["master_user"] == "guest"

        # Guest can now control the video
        seek_result = await activity.user_action("guest", {
            "type": "activity:youtube:seek",
            "time": 30.0
        })

        assert seek_result["type"] == "youtube_seek"
        assert activity.state["current_time"] == 30.0

        # Clean up
        await activity.stop()
        await manager.disconnect(guest_ws)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_state_synchronization_timing(self):
        """Test that state updates are properly synchronized with timing."""
        manager = ConnectionManager()

        # Create websocket with timing tracking
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()

        room = "sync_timing"

        await manager.connect(ws, room, "user")
        activity = manager.room_activities[room]

        # Load video and start playing
        await activity.user_action("user", {
            "type": "activity:youtube:load_video",
            "video_id": "test123",
            "start_time": 10.0
        })

        start_time = time.time()
        await activity.user_action("user", {
            "type": "activity:youtube:play"
        })

        # Wait a bit
        await asyncio.sleep(0.1)

        # Check accurate time calculation
        current_time = activity._get_accurate_current_time()
        elapsed = time.time() - start_time

        # Should be approximately start_time + elapsed
        expected_min = 10.0 + (elapsed * 0.8)  # Allow some variance
        expected_max = 10.0 + (elapsed * 1.2)

        assert expected_min <= current_time <= expected_max

        # Test state report from authoritative user
        reported_time = 15.0
        state_report = await activity.user_action("user", {
            "type": "activity:youtube:state_report",
            "current_time": reported_time,
            "is_playing": True,
            "playback_rate": 1.0
        })

        assert state_report["type"] == "state_report_accepted"
        assert activity.state["current_time"] == reported_time

        # Clean up
        await activity.stop()
        await manager.disconnect(ws)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_youtube_actions(self):
        """Test handling concurrent YouTube actions from multiple users."""
        manager = ConnectionManager()

        # Create multiple websockets
        num_users = 5
        websockets = []
        usernames = [f"user{i}" for i in range(num_users)]

        for i in range(num_users):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)

        room = "concurrent_youtube"

        # Connect all users
        for i, username in enumerate(usernames):
            await manager.connect(websockets[i], room, username)

        activity = manager.room_activities[room]

        # First user loads video
        await activity.user_action(usernames[0], {
            "type": "activity:youtube:load_video",
            "video_id": "concurrent_test"
        })

        # All users try to play/pause simultaneously
        actions = []
        for i, username in enumerate(usernames):
            action_type = "activity:youtube:play" if i % 2 == 0 else "activity:youtube:pause"
            action_task = asyncio.create_task(
                activity.user_action(username, {"type": action_type})
            )
            actions.append(action_task)

        results = await asyncio.gather(*actions, return_exceptions=True)

        # All actions should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception)
            assert result["type"] in ["youtube_play", "youtube_pause"]

        # State should be consistent (either playing or paused)
        assert isinstance(activity.state["is_playing"], bool)
        assert activity.state["authoritative_user"] in usernames

        # Sync requests from all users should work
        sync_actions = []
        for username in usernames:
            sync_task = asyncio.create_task(
                activity.user_action(username, {"type": "activity:youtube:sync_request"})
            )
            sync_actions.append(sync_task)

        sync_results = await asyncio.gather(*sync_actions, return_exceptions=True)

        # All sync requests should succeed
        for result in sync_results:
            assert not isinstance(result, Exception)
            assert result["type"] == "youtube_sync_response"
            assert result["video_id"] == "concurrent_test"

        # Clean up
        await activity.stop()
        for ws in websockets:
            await manager.disconnect(ws)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_youtube_activity_with_room_host_changes(self):
        """Test YouTube activity behavior when room host changes."""
        manager = ConnectionManager()

        # Create websockets
        original_host_ws = AsyncMock()
        original_host_ws.accept = AsyncMock()
        original_host_ws.send_json = AsyncMock()
        original_host_ws.close = AsyncMock()

        new_host_ws = AsyncMock()
        new_host_ws.accept = AsyncMock()
        new_host_ws.send_json = AsyncMock()
        new_host_ws.close = AsyncMock()

        room = "host_change_youtube"

        # Connect users
        await manager.connect(original_host_ws, room, "original_host")
        await manager.connect(new_host_ws, room, "new_host")

        activity = manager.room_activities[room]

        # Original host loads video and becomes YouTube master
        await activity.user_action("original_host", {
            "type": "activity:youtube:load_video",
            "video_id": "host_test"
        })

        assert activity.state["master_user"] == "original_host"
        assert manager.room_hosts[room] == "original_host"

        # Original host (room host) can seek
        seek_result = await activity.user_action("original_host", {
            "type": "activity:youtube:seek",
            "time": 30.0
        })
        assert seek_result["type"] == "youtube_seek"

        # New user cannot seek (not YouTube master)
        seek_fail = await activity.user_action("new_host", {
            "type": "activity:youtube:seek",
            "time": 60.0
        })
        assert seek_fail["type"] == "error"

        # Original host (room host) disconnects
        await manager.disconnect(original_host_ws)

        # New user becomes room host, but YouTube master should transfer too
        assert manager.room_hosts[room] == "new_host"
        assert activity.state["master_user"] == "new_host"

        # New host can now seek
        seek_result2 = await activity.user_action("new_host", {
            "type": "activity:youtube:seek",
            "time": 45.0
        })
        assert seek_result2["type"] == "youtube_seek"
        assert activity.state["current_time"] == 45.0

        # Clean up
        await activity.stop()
        await manager.disconnect(new_host_ws)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_youtube_error_scenarios(self):
        """Test error handling in YouTube activity integration."""
        manager = ConnectionManager()

        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()

        room = "youtube_errors"

        await manager.connect(ws, room, "user")
        activity = manager.room_activities[room]

        # Try to play without loading video first
        play_result = await activity.user_action("user", {
            "type": "activity:youtube:play"
        })
        assert play_result["type"] == "error"
        assert "No video loaded" in play_result["message"]

        # Try to seek without loading video
        seek_result = await activity.user_action("user", {
            "type": "activity:youtube:seek",
            "time": 30.0
        })
        assert seek_result["type"] == "error"

        # Load video and test invalid actions
        await activity.user_action("user", {
            "type": "activity:youtube:load_video",
            "video_id": "error_test"
        })

        # Try invalid playback rate
        rate_result = await activity.user_action("user", {
            "type": "activity:youtube:set_rate",
            "rate": -1.0  # Invalid rate
        })
        assert rate_result["type"] == "error"
        assert "Invalid playback rate" in rate_result["message"]

        # Try unknown action
        unknown_result = await activity.user_action("user", {
            "type": "activity:youtube:unknown_action"
        })
        assert unknown_result["type"] == "error"
        assert "Unknown action" in unknown_result["message"]

        # Clean up
        await activity.stop()
        await manager.disconnect(ws)