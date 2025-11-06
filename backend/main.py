from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set, Optional
import json
from datetime import datetime
from pathlib import Path
from activities.registry import activity_registry
from activities.base import ActivityType, ActivityManager

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Room-based connection manager with activity support
class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.client_info: Dict[WebSocket, Dict] = {}
        self.room_hosts: Dict[str, str] = {}  # room -> host username
        self.room_activities: Dict[str, ActivityManager] = {}  # room -> current activity

    async def connect(self, websocket: WebSocket, room: str, username: str):
        await websocket.accept()
        is_new_room = room not in self.rooms

        if is_new_room:
            self.rooms[room] = set()
            # First person to join is the host
            self.room_hosts[room] = username
            # Initialize with YouTube activity
            await self._create_room_activity(room, ActivityType.YOUTUBE)

        self.rooms[room].add(websocket)
        self.client_info[websocket] = {"room": room, "username": username}

        # Add user to current activity
        if room in self.room_activities:
            await self.room_activities[room].add_user(username)

        # Send current room and activity state
        await self._send_room_state(websocket, room)

    async def _create_room_activity(self, room: str, activity_type: ActivityType, config: Dict = None):
        """Create and start a new activity for the room"""
        # Stop existing activity
        if room in self.room_activities:
            await self.room_activities[room].stop()

        # Create new activity
        activity = activity_registry.create_activity(activity_type, room, config)
        activity.set_message_handler(self._activity_broadcast_handler)
        self.room_activities[room] = activity
        await activity.start()

    async def _activity_broadcast_handler(self, room: str, message: Dict, exclude_user: str = None, target_user: str = None):
        """Handle activity broadcasts to room members"""
        if target_user:
            await self.send_to_user(room, target_user, message)
        else:
            await self.broadcast_to_room(room, message, exclude_user=exclude_user)

    async def _send_room_state(self, websocket: WebSocket, room: str):
        """Send current room and activity state to user"""
        client_info = self.client_info[websocket]
        username = client_info["username"]

        # Send role information
        await websocket.send_json({
            "type": "role_assigned",
            "role": "host" if self.is_host(websocket) else "participant",
            "is_host": self.is_host(websocket),
            "host": self.room_hosts.get(room)
        })

        # Send activity state
        if room in self.room_activities:
            activity = self.room_activities[room]
            state = await activity.get_state_for_user(username)
            await websocket.send_json(state)

        # Send available activities
        await websocket.send_json({
            "type": "available_activities",
            "activities": activity_registry.get_available_activities()
        })

    async def disconnect(self, websocket: WebSocket):
        info = self.client_info.get(websocket)
        if info:
            room = info["room"]
            username = info["username"]

            # Remove from activity
            if room in self.room_activities:
                await self.room_activities[room].remove_user(username)

            # Remove from room
            if room in self.rooms:
                self.rooms[room].discard(websocket)

                if not self.rooms[room]:
                    # Room is empty, clean up all room data
                    del self.rooms[room]
                    if room in self.room_hosts:
                        del self.room_hosts[room]
                    if room in self.room_activities:
                        await self.room_activities[room].stop()
                        del self.room_activities[room]

            # Remove client info (use pop to avoid KeyError)
            self.client_info.pop(websocket, None)

    def is_host(self, websocket: WebSocket) -> bool:
        """Check if the websocket connection belongs to the room host"""
        info = self.client_info.get(websocket)
        if not info:
            return False
        room = info["room"]
        username = info["username"]
        return self.room_hosts.get(room) == username

    async def broadcast_to_room(self, room: str, message: dict, sender: WebSocket = None, exclude_user: str = None):
        """Broadcast message to all users in room"""
        if room in self.rooms:
            # Create a copy to avoid concurrent modification
            connections = list(self.rooms[room])
            disconnected = []

            for connection in connections:
                # Skip sender if specified
                if connection == sender:
                    continue

                # Skip specific user if specified
                if exclude_user:
                    client_info = self.client_info.get(connection)
                    if client_info and client_info["username"] == exclude_user:
                        continue

                try:
                    await connection.send_json(message)
                except:
                    # Client disconnected, mark for removal
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.rooms[room].discard(conn)
                if conn in self.client_info:
                    del self.client_info[conn]

    async def send_to_user(self, room: str, username: str, message: dict):
        """Send message to specific user in room"""
        if room in self.rooms:
            # Create a copy to avoid concurrent modification
            connections = list(self.rooms[room])

            for connection in connections:
                client_info = self.client_info.get(connection)
                if client_info and client_info["username"] == username:
                    try:
                        await connection.send_json(message)
                        return  # Found and sent to user
                    except:
                        # Client disconnected, remove it
                        self.rooms[room].discard(connection)
                        if connection in self.client_info:
                            del self.client_info[connection]

    async def change_room_activity(self, room: str, user_id: str, activity_type: ActivityType, config: Dict = None) -> tuple[bool, str]:
        """Change room activity with permission check"""
        # Check if user is host
        is_host = False
        for ws, info in self.client_info.items():
            if info["room"] == room and info["username"] == user_id:
                is_host = self.is_host(ws)
                break

        if not is_host:
            return False, "Only the room host can change activities"

        try:
            # Create new activity
            await self._create_room_activity(room, activity_type, config)

            # Add all current users to new activity
            for info in self.client_info.values():
                if info["room"] == room:
                    await self.room_activities[room].add_user(info["username"])

            # Broadcast activity change
            await self.broadcast_to_room(room, {
                "type": "activity_changed",
                "activity_type": activity_type.value,
                "activity_name": activity_type.display_name,
                "changed_by": user_id
            })

            # Send new activity state to all users
            if room in self.room_activities:
                activity = self.room_activities[room]
                for ws, info in self.client_info.items():
                    if info["room"] == room:
                        state = await activity.get_state_for_user(info["username"])
                        await ws.send_json(state)

            return True, f"Activity changed to {activity_type.display_name}"

        except Exception as e:
            return False, f"Failed to change activity: {str(e)}"

manager = ConnectionManager()

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await manager.connect(websocket, room, username)

    # Notify room that user joined
    await manager.broadcast_to_room(
        room,
        {"type": "user_joined", "username": username, "message": f"{username} joined the room"},
        sender=websocket
    )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            message_type = message_data.get("type", "message")

            if message_type == "change_activity":
                # Handle activity change request
                activity_type_str = message_data.get("activity_type", "")
                config = message_data.get("config", {})

                if not activity_registry.is_valid_activity_type(activity_type_str):
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Invalid activity type: {activity_type_str}"
                    })
                    continue

                activity_type = ActivityType(activity_type_str)
                success, message = await manager.change_room_activity(room, username, activity_type, config)

                if not success:
                    await websocket.send_json({
                        "type": "activity_change_error",
                        "message": message
                    })

            elif message_type.startswith("activity:"):
                # Handle activity-specific actions
                if room in manager.room_activities:
                    activity = manager.room_activities[room]
                    try:
                        result = await activity.user_action(username, message_data)

                        # Send result back to user if it's not a broadcast
                        if result and not result.get("type", "").startswith("broadcast"):
                            await websocket.send_json(result)

                        # For state-changing actions, send updated activity state to all users
                        state_changing_actions = [
                            "youtube_video_loaded",
                            "youtube_play",
                            "youtube_pause",
                            "youtube_seek",
                            "youtube_rate_changed",
                            "snake_joined",
                            "snake_game_started",
                            "snake_game_restarted"
                        ]

                        if result and result.get("type") in state_changing_actions:
                            # Send updated activity state to all users in room
                            for ws, info in manager.client_info.items():
                                if info["room"] == room:
                                    try:
                                        state = await activity.get_state_for_user(info["username"])
                                        await ws.send_json(state)
                                    except:
                                        # Client may have disconnected
                                        pass

                        # Handle chat messages specially
                        if result and result.get("type") == "message":
                            # Send to others in room
                            await manager.broadcast_to_room(room, result, sender=websocket)
                            # Send confirmation back to sender
                            await websocket.send_json({
                                **result,
                                "own_message": True
                            })

                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Activity action failed: {str(e)}"
                        })

            elif message_type == "get_room_info":
                # Send current room information
                activity = manager.room_activities.get(room)
                await websocket.send_json({
                    "type": "room_info",
                    "room_id": room,
                    "host": manager.room_hosts.get(room),
                    "current_activity": activity.activity_type.value if activity else None,
                    "available_activities": activity_registry.get_available_activities(),
                    "user_count": len(manager.rooms.get(room, set()))
                })

            else:
                # Handle as regular chat message (persistent across all activities)
                if message_data.get("type") == "message" or "message" in message_data:
                    message_text = message_data.get("message", "")
                    if message_text:
                        # Create chat message
                        chat_message = {
                            "type": "message",
                            "username": username,
                            "message": message_text
                        }

                        # Send to others in room
                        await manager.broadcast_to_room(room, chat_message, sender=websocket)
                        # Send confirmation back to sender
                        await websocket.send_json({
                            **chat_message,
                            "own_message": True
                        })
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_data.get('type', 'unknown')}"
                    })

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.broadcast_to_room(
            room,
            {"type": "user_left", "username": username, "message": f"{username} left the room"}
        )

@app.get("/")
async def root():
    return {"message": "WebSocket server is running"}

# Debug log file setup
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log rotation settings
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_LOG_BACKUPS = 5  # Keep 5 backup files

def get_log_file_path() -> Path:
    """Get today's log file path"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"debug-{date_str}.log"

def rotate_log_file(log_file: Path):
    """Rotate log file if it exceeds max size"""
    if not log_file.exists():
        return

    if log_file.stat().st_size >= MAX_LOG_SIZE:
        # Rotate existing backups
        for i in range(MAX_LOG_BACKUPS - 1, 0, -1):
            old_backup = log_file.with_suffix(f".log.{i}")
            new_backup = log_file.with_suffix(f".log.{i + 1}")
            if old_backup.exists():
                if new_backup.exists():
                    new_backup.unlink()
                old_backup.rename(new_backup)

        # Move current log to .1
        backup = log_file.with_suffix(".log.1")
        if backup.exists():
            backup.unlink()
        log_file.rename(backup)

        # Delete oldest backup if it exceeds MAX_LOG_BACKUPS
        oldest_backup = log_file.with_suffix(f".log.{MAX_LOG_BACKUPS + 1}")
        if oldest_backup.exists():
            oldest_backup.unlink()

@app.post("/api/debug-log")
async def receive_debug_log(log_data: dict):
    """Receive and save debug logs from frontend"""
    try:
        log_file = get_log_file_path()

        # Rotate log file if needed (before writing)
        rotate_log_file(log_file)

        # Format log entry
        timestamp = log_data.get("timestamp", datetime.now().isoformat())
        message = log_data.get("message", "")
        data = log_data.get("data", "")

        log_entry = f"[{timestamp}] {message}"
        if data:
            log_entry += f" {json.dumps(data)}"
        log_entry += "\n"

        # Append to file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

        return {"status": "logged", "file": str(log_file)}
    except Exception as e:
        print(f"Error writing log: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/debug-logs")
async def get_debug_logs():
    """Get logs from today's log file"""
    try:
        log_file = get_log_file_path()
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.read()
            return {"logs": logs, "file": str(log_file)}
        else:
            return {"logs": "", "file": str(log_file), "message": "No logs for today"}
    except Exception as e:
        return {"logs": "", "error": str(e)}