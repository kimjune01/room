import asyncio
import time
from typing import Dict, Any
from .base import ActivityManager, ActivityType

class YouTubeSyncActivity(ActivityManager):
    def __init__(self, room_id: str, config: Dict[str, Any] = None):
        super().__init__(room_id, ActivityType.YOUTUBE)

        config = config or {}
        self.state = {
            'video_id': config.get('video_id', None),
            'current_time': 0.0,
            'is_playing': False,
            'playback_rate': 1.0,
            'last_action_time': time.time(),
            'buffering_users': set(),  # Users currently buffering
            'sync_tolerance': 2.0,  # Seconds of acceptable desync
            'last_state_update': time.time(),  # When state was last updated by any client
            'last_action': None,  # Track the last user action for display
            'user_action_timestamps': {},  # Track last action time per user for throttling
            'last_action_user': None,  # Track who performed the last action (for sync purposes)
            'master_user': None,  # User with master control
            'authoritative_user': None  # User with authoritative state
        }

        # Universal throttle settings (seconds between actions per user)
        self.action_throttles = {
            'load_video': 3.0,    # Prevent video spam
            'seek': 1.0,          # Prevent seek spam
            'set_rate': 1.0,      # Prevent rate spam
            'play': 0.5,          # Allow quick play/pause
            'pause': 0.5,         # Allow quick play/pause
            'sync_request': 1.0,  # Limit sync requests
            'request_master': 2.0 # Limit master requests
        }

    async def start(self):
        """Start YouTube sync activity"""
        await super().start()
        self.task = asyncio.create_task(self._sync_loop())
        print(f"YouTube sync started for room {self.room_id}")

    async def stop(self):
        """Stop YouTube sync activity"""
        await super().stop()
        print(f"YouTube sync stopped for room {self.room_id}")

    async def _sync_loop(self):
        """Maintain accurate time tracking using server-side calculation"""
        while self.running:
            now = time.time()

            # Use synthetic time calculation for playing videos
            if (self.state['is_playing'] and
                not self.state['buffering_users'] and
                now - self.state['last_state_update'] > 5.0):  # Update every 5 seconds

                # Fall back to synthetic calculation
                elapsed = now - self.state['last_action_time']
                self.state['current_time'] += elapsed * self.state['playback_rate']
                self.state['last_action_time'] = now
                self.state['last_state_update'] = now

                # Broadcast updated state
                await self._broadcast_sync_update()

            await asyncio.sleep(2.0)  # Less frequent polling

    async def _broadcast_sync_update(self):
        """Broadcast current sync state to all users"""
        current_time = self._get_accurate_current_time()

        await self.broadcast_to_room({
            "type": "youtube_sync_update",
            "video_id": self.state['video_id'],
            "current_time": current_time,
            "is_playing": self.state['is_playing'],
            "playback_rate": self.state['playback_rate'],
            "last_action_user": self.state['last_action_user'],
            "server_timestamp": time.time()
        })



    def _check_action_throttle(self, user_id: str, action_type: str) -> bool:
        """Check if user can perform action based on throttle settings"""
        if action_type not in self.action_throttles:
            return True  # No throttle for unknown actions

        throttle_time = self.action_throttles[action_type]
        now = time.time()

        # Get user's last action timestamp for this action type
        user_key = f"{user_id}:{action_type}"
        last_action = self.state['user_action_timestamps'].get(user_key, 0)

        if now - last_action >= throttle_time:
            # Update timestamp and allow action
            self.state['user_action_timestamps'][user_key] = now
            return True

        return False

    def _get_accurate_current_time(self) -> float:
        """Calculate accurate current time based on elapsed time"""
        current_time = self.state['current_time']
        if self.state['is_playing'] and not self.state['buffering_users']:
            elapsed = time.time() - self.state['last_action_time']
            current_time += elapsed * self.state['playback_rate']
        return current_time

    async def user_action(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle video control actions"""
        action_type = action.get("type", "").replace("activity:youtube:", "")

        # Check throttle - anyone can do any action, but not too frequently
        if not self._check_action_throttle(user_id, action_type):
            throttle_time = self.action_throttles.get(action_type, 1.0)
            return {"type": "error", "message": f"Please wait {throttle_time}s between {action_type.replace('_', ' ')} actions"}

        if action_type == "load_video":
            return await self._handle_load_video(user_id, action)
        elif action_type == "play":
            return await self._handle_play(user_id)
        elif action_type == "pause":
            return await self._handle_pause(user_id)
        elif action_type == "seek":
            return await self._handle_seek(user_id, action)
        elif action_type == "set_rate":
            return await self._handle_set_rate(user_id, action)
        elif action_type == "sync_request":
            return await self._handle_sync_request(user_id)
        elif action_type == "buffer_start":
            return await self._handle_buffer_start(user_id)
        elif action_type == "buffer_end":
            return await self._handle_buffer_end(user_id)
        elif action_type == "request_master":
            return await self._handle_request_master(user_id)
        elif action_type == "state_report":
            return await self._handle_state_report(user_id, action)

        return {"type": "error", "message": f"Unknown YouTube action: {action_type}"}


    async def _handle_load_video(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle loading a new video"""
        video_id = action.get("video_id", "").strip()
        if not video_id:
            return {"type": "error", "message": "Video ID required"}

        # Reset state for new video
        self.state['video_id'] = video_id
        self.state['current_time'] = action.get("start_time", 0.0)
        self.state['is_playing'] = False
        self.state['playback_rate'] = 1.0
        self.state['last_action_time'] = time.time()
        self.state['last_action_user'] = user_id  # Track who loaded the video
        self.state['buffering_users'] = set()

        await self.broadcast_to_room({
            "type": "youtube_video_loaded",
            "video_id": video_id,
            "loaded_by": user_id,
            "current_time": self.state['current_time']
        })

        # Track action for display
        self.state['last_action'] = {
            'user': user_id,
            'type': 'load_video',
            'timestamp': time.time()
        }

        return {"type": "youtube_video_loaded", "video_id": video_id}

    async def _handle_play(self, user_id: str) -> Dict[str, Any]:
        """Handle play action"""
        if not self.state['video_id']:
            return {"type": "error", "message": "No video loaded"}

        # Don't play if users are buffering (but be more permissive for democratic control)
        if self.state['buffering_users']:
            print(f"DEBUG: Play blocked for {user_id}, buffering users: {self.state['buffering_users']}")
        self.state['is_playing'] = True
        self.state['last_action_time'] = time.time()
        self.state['last_action_user'] = user_id  # Track who performed the action

        await self.broadcast_to_room({
            "type": "youtube_play",
            "current_time": self.state['current_time'],
            "is_playing": True,
            "triggered_by": user_id,
            "last_action_user": user_id,
            "server_timestamp": time.time()
        })

        # Track action for display
        self.state['last_action'] = {
            'user': user_id,
            'type': 'play',
            'timestamp': time.time()
        }

        return {"type": "youtube_play", "current_time": self.state['current_time']}

    async def _handle_pause(self, user_id: str) -> Dict[str, Any]:
        """Handle pause action"""
        if not self.state['video_id']:
            return {"type": "error", "message": "No video loaded"}

        # Update current time before pausing
        if self.state['is_playing']:
            elapsed = time.time() - self.state['last_action_time']
            self.state['current_time'] += elapsed * self.state['playback_rate']

        self.state['is_playing'] = False
        self.state['last_action_time'] = time.time()
        self.state['last_action_user'] = user_id  # Track who performed the action

        await self.broadcast_to_room({
            "type": "youtube_pause",
            "current_time": self.state['current_time'],
            "is_playing": False,
            "triggered_by": user_id,
            "last_action_user": user_id,
            "server_timestamp": time.time()
        })

        # Track action for display
        self.state['last_action'] = {
            'user': user_id,
            'type': 'pause',
            'timestamp': time.time()
        }

        return {"type": "youtube_pause", "current_time": self.state['current_time']}

    async def _handle_seek(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle seek action"""
        if not self.state['video_id']:
            return {"type": "error", "message": "No video loaded"}

        seek_time = action.get("time", 0.0)
        if seek_time < 0:
            seek_time = 0.0

        self.state['current_time'] = seek_time
        self.state['last_action_time'] = time.time()
        self.state['last_action_user'] = user_id  # Track who performed the action

        await self.broadcast_to_room({
            "type": "youtube_seek",
            "current_time": seek_time,
            "triggered_by": user_id,
            "last_action_user": user_id,
            "server_timestamp": time.time()
        })

        # Track action for display
        self.state['last_action'] = {
            'user': user_id,
            'type': 'seek',
            'timestamp': time.time()
        }

        return {"type": "youtube_seek", "current_time": seek_time}

    async def _handle_set_rate(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle playback rate change"""
        rate = action.get("rate", 1.0)
        if rate <= 0 or rate > 2.0:
            return {"type": "error", "message": "Invalid playback rate"}

        # Update time before changing rate
        if self.state['is_playing']:
            elapsed = time.time() - self.state['last_action_time']
            self.state['current_time'] += elapsed * self.state['playback_rate']

        self.state['playback_rate'] = rate
        self.state['last_action_time'] = time.time()

        # Track action for display
        self.state['last_action'] = {
            'user': user_id,
            'type': 'set_rate',
            'timestamp': time.time()
        }

        await self.broadcast_to_room({
            "type": "youtube_rate_changed",
            "playback_rate": rate,
            "current_time": self.state['current_time'],
            "triggered_by": user_id
        })

        return {"type": "youtube_rate_changed", "playback_rate": rate}

    async def _handle_sync_request(self, user_id: str) -> Dict[str, Any]:
        """Handle sync request from user"""
        current_time = self._get_accurate_current_time()

        # Track action for display
        self.state['last_action'] = {
            'user': user_id,
            'type': 'sync_request',
            'timestamp': time.time()
        }

        return {
            "type": "youtube_sync_response",
            "video_id": self.state['video_id'],
            "current_time": current_time,
            "is_playing": self.state['is_playing'],
            "playback_rate": self.state['playback_rate'],
            "server_timestamp": time.time()
        }

    async def _handle_buffer_start(self, user_id: str) -> Dict[str, Any]:
        """Handle user starting to buffer"""
        self.state['buffering_users'].add(user_id)
        print(f"DEBUG: User {user_id} started buffering. Total buffering: {self.state['buffering_users']}")

        # Pause video if someone starts buffering
        if self.state['is_playing']:
            await self._handle_pause(user_id)

        await self.broadcast_to_room({
            "type": "youtube_user_buffering",
            "user_id": user_id,
            "buffering_count": len(self.state['buffering_users'])
        }, exclude_user=user_id)

        return {"type": "youtube_buffer_start", "message": "Buffering started"}

    async def _handle_buffer_end(self, user_id: str) -> Dict[str, Any]:
        """Handle user finishing buffering"""
        self.state['buffering_users'].discard(user_id)
        print(f"DEBUG: User {user_id} finished buffering. Remaining: {self.state['buffering_users']}")

        await self.broadcast_to_room({
            "type": "youtube_user_buffer_end",
            "user_id": user_id,
            "buffering_count": len(self.state['buffering_users'])
        }, exclude_user=user_id)

        # Auto-resume if no one is buffering and there's a master
        if not self.state['buffering_users'] and self.state['master_user']:
            # Small delay to let everyone catch up
            await asyncio.sleep(0.5)
            if not self.state['buffering_users']:  # Double check
                await self._handle_play(self.state['master_user'])

        return {"type": "youtube_buffer_end", "message": "Buffering ended"}

    async def _handle_request_master(self, user_id: str) -> Dict[str, Any]:
        """Handle request for master control"""
        # If no master or master is not in room, assign new master
        if self.state['master_user'] is None or self.state['master_user'] not in self.users:
            self.state['master_user'] = user_id

            # Track action for display
            self.state['last_action'] = {
                'user': user_id,
                'type': 'request_master',
                'timestamp': time.time()
            }

            await self.broadcast_to_room({
                "type": "youtube_master_changed",
                "new_master": user_id
            })

            return {"type": "youtube_master_assigned", "message": "You are now the master"}
        else:
            return {"type": "error", "message": f"Master control is held by {self.state['master_user']}"}

    async def add_user(self, user_id: str):
        """Add user to YouTube activity"""
        await super().add_user(user_id)

    async def remove_user(self, user_id: str):
        """Remove user from YouTube activity"""
        await super().remove_user(user_id)

        # Remove from buffering users
        self.state['buffering_users'].discard(user_id)

        # Clean up user's throttle timestamps to prevent memory leak
        keys_to_remove = [key for key in self.state['user_action_timestamps'].keys()
                          if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self.state['user_action_timestamps'][key]

        # Clear master/authoritative if this user held them
        if self.state.get('master_user') == user_id:
            self.state['master_user'] = None
        if self.state.get('authoritative_user') == user_id:
            self.state['authoritative_user'] = None

    async def _handle_state_report(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle state report from authoritative client"""
        # Only accept reports from the authoritative user
        if self.state['authoritative_user'] != user_id:
            return {"type": "error", "message": "Only authoritative user can report state"}

        # Check if this is a stale report - don't accept reports older than recent server actions
        # This prevents race conditions where host acts, becomes authoritative, then sends old state
        client_timestamp = action.get("client_timestamp", 0)
        if client_timestamp > 0 and client_timestamp < self.state['last_action_time']:
            print(f"DEBUG: Rejecting stale state report from {user_id}. "
                  f"Report time: {client_timestamp}, Last action: {self.state['last_action_time']}")
            return {"type": "state_report_rejected", "message": "Stale state report"}

        # Update state from client report
        reported_time = action.get("current_time", self.state['current_time'])
        reported_playing = action.get("is_playing", self.state['is_playing'])
        reported_rate = action.get("playback_rate", self.state['playback_rate'])

        self.state['current_time'] = reported_time
        self.state['is_playing'] = reported_playing
        self.state['playback_rate'] = reported_rate
        self.state['last_state_update'] = time.time()

        # Broadcast updated state to all other clients
        await self.broadcast_to_room({
            "type": "youtube_sync_update",
            "video_id": self.state['video_id'],
            "current_time": reported_time,
            "is_playing": reported_playing,
            "playback_rate": reported_rate,
            "master_user": self.state['master_user'],
            "authoritative_user": user_id,
            "server_timestamp": time.time()
        }, exclude_user=user_id)  # Don't send back to reporting client

        return {"type": "state_report_accepted"}

    async def get_state_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get current YouTube sync state for user"""
        current_time = self._get_accurate_current_time()

        return {
            "type": "activity_state",
            "activity_type": self.activity_type.value,
            "activity_name": self.activity_type.display_name,
            "state": {
                "video_id": self.state['video_id'],
                "current_time": current_time,
                "is_playing": self.state['is_playing'],
                "playback_rate": self.state['playback_rate'],
                "last_action_user": self.state['last_action_user'],
                "buffering_users": list(self.state['buffering_users']),
                "is_buffering": user_id in self.state['buffering_users'],
                "last_action": self.state['last_action']
            },
            "users": list(self.users),
            "server_timestamp": time.time()
        }