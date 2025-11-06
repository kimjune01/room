from abc import ABC, abstractmethod
from enum import Enum
import asyncio
from typing import Dict, Any, Set
from datetime import datetime

class ActivityType(Enum):
    SNAKE = "snake"
    YOUTUBE = "youtube"

    @property
    def display_name(self) -> str:
        names = {
            ActivityType.SNAKE: "🐍 Snake Game",
            ActivityType.YOUTUBE: "📺 Watch Together"
        }
        return names[self]

    @property
    def description(self) -> str:
        descriptions = {
            ActivityType.SNAKE: "Multiplayer snake game with real-time action",
            ActivityType.YOUTUBE: "Synchronized video watching experience"
        }
        return descriptions[self]

class ActivityManager(ABC):
    def __init__(self, room_id: str, activity_type: ActivityType):
        self.room_id = room_id
        self.activity_type = activity_type
        self.state: Dict[str, Any] = {}
        self.users: Set[str] = set()
        self.created_at = datetime.now()
        self.last_update = datetime.now()
        self.running = False
        self.task: asyncio.Task = None
        self.message_handler = None  # Will be set by connection manager

    @abstractmethod
    async def start(self):
        """Start the activity"""
        self.running = True

    @abstractmethod
    async def stop(self):
        """Stop the activity"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        # Break circular reference to prevent memory leak
        self.message_handler = None

    @abstractmethod
    async def user_action(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user input and return response"""
        pass

    @abstractmethod
    async def get_state_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get current state for a user"""
        pass

    async def add_user(self, user_id: str):
        """Add user to activity"""
        self.users.add(user_id)
        self.last_update = datetime.now()

    async def remove_user(self, user_id: str):
        """Remove user from activity"""
        self.users.discard(user_id)
        self.last_update = datetime.now()

    async def broadcast_to_room(self, message: Dict[str, Any], exclude_user: str = None):
        """Broadcast message to all users in room"""
        if self.message_handler:
            await self.message_handler(self.room_id, message, exclude_user)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if self.message_handler:
            await self.message_handler(self.room_id, message, exclude_user=None, target_user=user_id)

    def set_message_handler(self, handler):
        """Set the message broadcast handler"""
        self.message_handler = handler