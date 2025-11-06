from .base import ActivityManager, ActivityType
from typing import Dict, Any

class ChatActivity(ActivityManager):
    def __init__(self, room_id: str):
        super().__init__(room_id, ActivityType.CHAT)
        self.state = {
            "message_count": 0,
            "last_message": None
        }

    async def start(self):
        """Start chat activity"""
        await super().start()
        print(f"Chat activity started for room {self.room_id}")

    async def stop(self):
        """Stop chat activity"""
        await super().stop()
        print(f"Chat activity stopped for room {self.room_id}")

    async def user_action(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat message"""
        if action.get("type") == "message":
            message_text = action.get("message", "")

            # Update state
            self.state["message_count"] += 1
            self.state["last_message"] = {
                "user": user_id,
                "text": message_text,
                "timestamp": str(self.last_update)
            }

            # Return the message to be broadcast
            return {
                "type": "message",
                "username": user_id,
                "message": message_text
            }

        return {"type": "error", "message": "Unknown action for chat"}

    async def get_state_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get current chat state"""
        return {
            "type": "activity_state",
            "activity_type": self.activity_type.value,
            "activity_name": self.activity_type.display_name,
            "state": self.state,
            "users": list(self.users)
        }