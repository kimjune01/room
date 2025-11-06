import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from activities.youtube import YouTubeSyncActivity
from activities.base import ActivityType


class TestYouTubeSyncActivity:
    """Test YouTube synchronization activity."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_activity_initialization(self):
        """Test YouTube activity initialization."""
        room_id = "test_room"
        activity = YouTubeSyncActivity(room_id)

        assert activity.room_id == room_id
        assert activity.activity_type == ActivityType.YOUTUBE
        assert activity.state['video_id'] is None
        assert activity.state['current_time'] == 0.0
        assert activity.state['is_playing'] is False
        assert activity.state['master_user'] is None
        assert activity.state['authoritative_user'] is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_and_stop_activity(self, youtube_activity):
        """Test starting and stopping YouTube activity."""
        activity = youtube_activity

        assert activity.running is True
        assert activity.task is not None

        await activity.stop()

        assert activity.running is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_load_video_as_master(self, youtube_activity):
        """Test loading video as master user."""
        activity = youtube_activity
        user_id = "test_user"

        # Add user and make them master
        await activity.add_user(user_id)

        # Load video
        action = {
            "type": "activity:youtube:load_video",
            "video_id": "dQw4w9WgXcQ",
            "start_time": 30.0
        }

        result = await activity.user_action(user_id, action)

        assert result["type"] == "youtube_video_loaded"
        assert result["video_id"] == "dQw4w9WgXcQ"
        assert activity.state["video_id"] == "dQw4w9WgXcQ"
        assert activity.state["current_time"] == 30.0
        assert activity.state["authoritative_user"] == user_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_load_video_non_master_fails(self, youtube_activity):
        """Test that non-master cannot load video."""
        activity = youtube_activity
        master = "master_user"
        guest = "guest_user"

        # Add both users, first is master
        await activity.add_user(master)
        await activity.add_user(guest)

        # Guest tries to load video
        action = {
            "type": "activity:youtube:load_video",
            "video_id": "dQw4w9WgXcQ"
        }

        result = await activity.user_action(guest, action)

        assert result["type"] == "error"
        assert "Only the master user" in result["message"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_play_pause_any_user(self, youtube_activity, sample_video_data):
        """Test that any user can play/pause."""
        activity = youtube_activity
        master = "master_user"
        guest = "guest_user"

        # Add users and load video
        await activity.add_user(master)
        await activity.add_user(guest)

        # Master loads video
        load_action = {
            "type": "activity:youtube:load_video",
            "video_id": sample_video_data["video_id"]
        }
        await activity.user_action(master, load_action)

        # Guest tries to play - should work
        play_action = {"type": "activity:youtube:play"}
        result = await activity.user_action(guest, play_action)

        assert result["type"] == "youtube_play"
        assert activity.state["is_playing"] is True
        assert activity.state["authoritative_user"] == guest

        # Master tries to pause - should work
        pause_action = {"type": "activity:youtube:pause"}
        result = await activity.user_action(master, pause_action)

        assert result["type"] == "youtube_pause"
        assert activity.state["is_playing"] is False
        assert activity.state["authoritative_user"] == master

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_seek_master_only(self, youtube_activity, sample_video_data):
        """Test that only master can seek."""
        activity = youtube_activity
        master = "master_user"
        guest = "guest_user"

        # Add users and load video
        await activity.add_user(master)
        await activity.add_user(guest)

        # Master loads video
        load_action = {
            "type": "activity:youtube:load_video",
            "video_id": sample_video_data["video_id"]
        }
        await activity.user_action(master, load_action)

        # Guest tries to seek - should fail
        seek_action = {
            "type": "activity:youtube:seek",
            "time": 60.0
        }
        result = await activity.user_action(guest, seek_action)

        assert result["type"] == "error"
        assert "Only the master user" in result["message"]

        # Master seeks - should work
        result = await activity.user_action(master, seek_action)

        assert result["type"] == "youtube_seek"
        assert activity.state["current_time"] == 60.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_playback_rate_master_only(self, youtube_activity, sample_video_data):
        """Test that only master can change playback rate."""
        activity = youtube_activity
        master = "master_user"
        guest = "guest_user"

        # Add users and load video
        await activity.add_user(master)
        await activity.add_user(guest)

        # Master loads video
        load_action = {
            "type": "activity:youtube:load_video",
            "video_id": sample_video_data["video_id"]
        }
        await activity.user_action(master, load_action)

        # Guest tries to change rate - should fail
        rate_action = {
            "type": "activity:youtube:set_rate",
            "rate": 1.5
        }
        result = await activity.user_action(guest, rate_action)

        assert result["type"] == "error"
        assert "Only the master user" in result["message"]

        # Master changes rate - should work
        result = await activity.user_action(master, rate_action)

        assert result["type"] == "youtube_rate_changed"
        assert activity.state["playback_rate"] == 1.5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_buffering_functionality(self, youtube_activity, sample_video_data):
        """Test buffering start/end functionality."""
        activity = youtube_activity
        user = "test_user"

        # Add user and load video
        await activity.add_user(user)

        load_action = {
            "type": "activity:youtube:load_video",
            "video_id": sample_video_data["video_id"]
        }
        await activity.user_action(user, load_action)

        # Start playing
        await activity.user_action(user, {"type": "activity:youtube:play"})
        assert activity.state["is_playing"] is True

        # Start buffering
        buffer_start_result = await activity.user_action(user, {"type": "activity:youtube:buffer_start"})

        assert buffer_start_result["type"] == "youtube_buffer_start"
        assert user in activity.state["buffering_users"]
        assert activity.state["is_playing"] is False  # Should auto-pause

        # End buffering
        buffer_end_result = await activity.user_action(user, {"type": "activity:youtube:buffer_end"})

        assert buffer_end_result["type"] == "youtube_buffer_end"
        assert user not in activity.state["buffering_users"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_request(self, youtube_activity, sample_video_data):
        """Test sync request functionality."""
        activity = youtube_activity
        user = "test_user"

        # Add user and load video
        await activity.add_user(user)

        # Set some state
        activity.state.update(sample_video_data)

        # Request sync
        result = await activity.user_action(user, {"type": "activity:youtube:sync_request"})

        assert result["type"] == "youtube_sync_response"
        assert result["video_id"] == sample_video_data["video_id"]
        assert result["current_time"] == sample_video_data["current_time"]
        assert result["is_playing"] == sample_video_data["is_playing"]
        assert result["playback_rate"] == sample_video_data["playback_rate"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_request_master_control(self, youtube_activity):
        """Test requesting master control."""
        activity = youtube_activity
        user1 = "user1"
        user2 = "user2"

        # Add first user (becomes master)
        await activity.add_user(user1)
        assert activity.state["master_user"] == user1

        # Add second user
        await activity.add_user(user2)

        # Second user requests master control - should fail
        result = await activity.user_action(user2, {"type": "activity:youtube:request_master"})

        assert result["type"] == "error"
        assert "Master control is held by" in result["message"]
        assert activity.state["master_user"] == user1  # Should remain unchanged

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_master_transfer_on_disconnect(self, youtube_activity):
        """Test master control transfer when master leaves."""
        activity = youtube_activity
        master = "master_user"
        guest = "guest_user"

        # Add users
        await activity.add_user(master)
        await activity.add_user(guest)

        assert activity.state["master_user"] == master

        # Remove master
        await activity.remove_user(master)

        # Guest should become new master
        assert activity.state["master_user"] == guest

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_state_report_authoritative_only(self, youtube_activity, sample_video_data):
        """Test that only authoritative user can report state."""
        activity = youtube_activity
        auth_user = "auth_user"
        other_user = "other_user"

        # Add users
        await activity.add_user(auth_user)
        await activity.add_user(other_user)

        # Set authoritative user
        activity.state["authoritative_user"] = auth_user

        # Other user tries to report state - should fail
        state_report = {
            "type": "activity:youtube:state_report",
            "current_time": 50.0,
            "is_playing": True,
            "playback_rate": 1.25
        }

        result = await activity.user_action(other_user, state_report)
        assert result["type"] == "error"
        assert "Only authoritative user" in result["message"]

        # Authoritative user reports state - should work
        result = await activity.user_action(auth_user, state_report)
        assert result["type"] == "state_report_accepted"
        assert activity.state["current_time"] == 50.0
        assert activity.state["is_playing"] is True
        assert activity.state["playback_rate"] == 1.25

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_state_for_user(self, youtube_activity, sample_video_data):
        """Test getting state for specific user."""
        activity = youtube_activity
        master = "master_user"
        guest = "guest_user"

        # Add users
        await activity.add_user(master)
        await activity.add_user(guest)

        # Set state
        activity.state.update(sample_video_data)
        activity.state["master_user"] = master
        activity.state["authoritative_user"] = guest

        # Get state for master
        master_state = await activity.get_state_for_user(master)

        assert master_state["type"] == "activity_state"
        assert master_state["activity_type"] == ActivityType.YOUTUBE.value
        assert master_state["state"]["video_id"] == sample_video_data["video_id"]
        assert master_state["state"]["is_master"] is True
        assert master_state["state"]["is_authoritative"] is False

        # Get state for guest
        guest_state = await activity.get_state_for_user(guest)

        assert guest_state["state"]["is_master"] is False
        assert guest_state["state"]["is_authoritative"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_time_calculation_accuracy(self, youtube_activity):
        """Test accurate time calculation during playback."""
        activity = youtube_activity
        user = "test_user"

        await activity.add_user(user)

        # Load and start video
        await activity.user_action(user, {
            "type": "activity:youtube:load_video",
            "video_id": "test_video",
            "start_time": 10.0
        })

        start_time = time.time()
        await activity.user_action(user, {"type": "activity:youtube:play"})

        # Simulate some time passing
        await asyncio.sleep(0.1)

        # Check that time calculation is reasonable
        current_time = activity._get_accurate_current_time()
        expected_min_time = 10.0 + 0.05  # At least 50ms should have passed

        assert current_time >= expected_min_time