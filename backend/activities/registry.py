from typing import Dict, List
from .base import ActivityManager, ActivityType
from .youtube import YouTubeSyncActivity

class ActivityRegistry:
    def __init__(self):
        self.activity_classes = {
            ActivityType.YOUTUBE: YouTubeSyncActivity,
        }

    def create_activity(self, activity_type: ActivityType, room_id: str, config: Dict = None) -> ActivityManager:
        """Create a new activity instance"""
        if activity_type not in self.activity_classes:
            raise ValueError(f"Unknown activity type: {activity_type}")

        activity_class = self.activity_classes[activity_type]

        # Create activity with config
        return activity_class(room_id, config or {})

    def get_available_activities(self) -> List[Dict[str, str]]:
        """Get list of available activities for UI"""
        return [
            {
                "type": activity.value,
                "name": activity.display_name,
                "description": activity.description
            }
            for activity in ActivityType
        ]

    def is_valid_activity_type(self, activity_type_str: str) -> bool:
        """Check if activity type string is valid"""
        try:
            ActivityType(activity_type_str)
            return True
        except ValueError:
            return False

# Global registry instance
activity_registry = ActivityRegistry()