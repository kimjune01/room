# Simple Room Activities Architecture

A lightweight, single-process approach to room activities using background tasks and in-memory state management.

## 🎯 Philosophy: Keep It Simple

**No microservices. No external dependencies. Just FastAPI + background tasks.**

- **Single Process**: Everything runs in the FastAPI application
- **Background Tasks**: Use asyncio tasks for game loops and simulations
- **In-Memory State**: Game state stored in Python dictionaries
- **Thread-Safe**: Simple locks for concurrent access
- **Fast Iteration**: Add new activities by adding new classes

## 🏗️ Simple Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI App   │
│   (React)       │◄──►│                 │
│                 │    │  ┌─────────────┐ │
└─────────────────┘    │  │ WebSocket   │ │
                       │  │ Handler     │ │
                       │  └─────────────┘ │
                       │  ┌─────────────┐ │
                       │  │ Activity    │ │
                       │  │ Manager     │ │
                       │  └─────────────┘ │
                       │  ┌─────────────┐ │
                       │  │ Background  │ │
                       │  │ Tasks       │ │
                       │  └─────────────┘ │
                       └─────────────────┘
```

## 🔧 Core Implementation

### Activity Manager Base Class

```python
from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any
from datetime import datetime

class ActivityManager(ABC):
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.state: Dict[str, Any] = {}
        self.users: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.last_update = datetime.now()
        self.running = False
        self.task: asyncio.Task = None

    @abstractmethod
    async def start(self):
        """Start the activity"""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the activity"""
        pass

    @abstractmethod
    async def user_action(self, user_id: str, action: Dict[str, Any]):
        """Handle user input"""
        pass

    @abstractmethod
    async def get_state_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get current state for a user"""
        pass

    async def add_user(self, user_id: str, user_data: Dict[str, Any]):
        """Add user to activity"""
        self.users[user_id] = user_data

    async def remove_user(self, user_id: str):
        """Remove user from activity"""
        if user_id in self.users:
            del self.users[user_id]
```

### Activity Types and Host Control

```python
from enum import Enum

class ActivityType(Enum):
    CHAT = "chat"
    SNAKE = "snake"
    YOUTUBE = "youtube"
    WHITEBOARD = "whiteboard"
    POLL = "poll"

    @property
    def display_name(self) -> str:
        names = {
            ActivityType.CHAT: "💬 Chat",
            ActivityType.SNAKE: "🐍 Snake Game",
            ActivityType.YOUTUBE: "📺 Watch Together",
            ActivityType.WHITEBOARD: "🎨 Whiteboard",
            ActivityType.POLL: "📊 Live Poll"
        }
        return names[self]

    @property
    def description(self) -> str:
        descriptions = {
            ActivityType.CHAT: "Text messaging and conversation",
            ActivityType.SNAKE: "Multiplayer snake game with real-time action",
            ActivityType.YOUTUBE: "Synchronized video watching experience",
            ActivityType.WHITEBOARD: "Collaborative drawing and brainstorming",
            ActivityType.POLL: "Real-time voting and surveys"
        }
        return descriptions[self]

class RoomRole(Enum):
    HOST = "host"        # Can change activities, kick users
    MODERATOR = "mod"    # Can moderate but not change activities
    PARTICIPANT = "user" # Regular user

class RoomActivityRegistry:
    def __init__(self):
        self.rooms: Dict[str, ActivityManager] = {}
        self.room_hosts: Dict[str, str] = {}  # room_id -> host_user_id
        self.user_roles: Dict[str, Dict[str, RoomRole]] = {}  # room_id -> {user_id -> role}
        self.activity_types = {
            ActivityType.CHAT: ChatActivity,
            ActivityType.SNAKE: SnakeGameActivity,
            ActivityType.YOUTUBE: YouTubeSyncActivity,
        }

    async def set_room_host(self, room_id: str, user_id: str):
        """Set room host (first user or explicit assignment)"""
        self.room_hosts[room_id] = user_id
        if room_id not in self.user_roles:
            self.user_roles[room_id] = {}
        self.user_roles[room_id][user_id] = RoomRole.HOST

    def get_user_role(self, room_id: str, user_id: str) -> RoomRole:
        """Get user's role in room"""
        if room_id not in self.user_roles:
            return RoomRole.PARTICIPANT
        return self.user_roles[room_id].get(user_id, RoomRole.PARTICIPANT)

    def can_change_activity(self, room_id: str, user_id: str) -> bool:
        """Check if user can change room activity"""
        return self.get_user_role(room_id, user_id) == RoomRole.HOST

    async def change_room_activity(self, room_id: str, user_id: str,
                                  activity_type: ActivityType,
                                  config: Dict = None) -> tuple[bool, str, ActivityManager]:
        """Change room activity with permission check"""

        # Check permissions
        if not self.can_change_activity(room_id, user_id):
            return False, "Only the room host can change activities", None

        # Validate activity type
        if activity_type not in self.activity_types:
            return False, f"Unknown activity type: {activity_type.value}", None

        # Stop existing activity
        if room_id in self.rooms:
            await self.rooms[room_id].stop()

        # Create new activity
        activity_class = self.activity_types[activity_type]
        activity = activity_class(room_id, config or {})

        self.rooms[room_id] = activity
        await activity.start()

        return True, f"Activity changed to {activity_type.display_name}", activity

    def get_room_activity(self, room_id: str) -> ActivityManager:
        return self.rooms.get(room_id)

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

# Global registry
activity_registry = RoomActivityRegistry()
```

## 🎮 Snake Game Implementation

### Game Loop with Background Task

```python
import asyncio
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

@dataclass
class Position:
    x: int
    y: int

class SnakeGameActivity(ActivityManager):
    def __init__(self, room_id: str, config: Dict = None):
        super().__init__(room_id)
        self.grid_width = config.get('width', 20)
        self.grid_height = config.get('height', 20)
        self.tick_rate = config.get('tick_rate', 10)  # ticks per second

        self.state = {
            'status': 'waiting',  # waiting, playing, finished
            'snakes': {},         # user_id -> snake data
            'food': [],           # food positions
            'scores': {},         # user_id -> score
        }

    async def start(self):
        """Start the game background task"""
        self.running = True
        self.task = asyncio.create_task(self._game_loop())

    async def stop(self):
        """Stop the game"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _game_loop(self):
        """Main game simulation loop"""
        while self.running:
            if self.state['status'] == 'playing':
                await self._update_game_state()
                await self._broadcast_state()

            # Sleep for tick interval
            await asyncio.sleep(1.0 / self.tick_rate)

    async def _update_game_state(self):
        """Update game state for one tick"""
        # Move all snakes
        for user_id, snake in self.state['snakes'].items():
            if not snake.get('alive', True):
                continue

            # Move snake head
            head = snake['positions'][0]
            direction = snake['direction']
            new_head = Position(
                head.x + direction.value[0],
                head.y + direction.value[1]
            )

            # Check wall collision
            if (new_head.x < 0 or new_head.x >= self.grid_width or
                new_head.y < 0 or new_head.y >= self.grid_height):
                snake['alive'] = False
                continue

            # Check self collision
            if new_head in snake['positions']:
                snake['alive'] = False
                continue

            # Check other snake collision
            for other_id, other_snake in self.state['snakes'].items():
                if other_id != user_id and new_head in other_snake['positions']:
                    snake['alive'] = False
                    break

            if not snake['alive']:
                continue

            # Move snake
            snake['positions'].insert(0, new_head)

            # Check food collision
            if new_head in self.state['food']:
                self.state['food'].remove(new_head)
                self.state['scores'][user_id] += 1
                self._spawn_food()
            else:
                # Remove tail if no food eaten
                snake['positions'].pop()

        # Check if game should end
        alive_snakes = [s for s in self.state['snakes'].values() if s.get('alive', True)]
        if len(alive_snakes) <= 1 and len(self.state['snakes']) > 1:
            self.state['status'] = 'finished'

    def _spawn_food(self):
        """Spawn food at random position"""
        while True:
            pos = Position(
                random.randint(0, self.grid_width - 1),
                random.randint(0, self.grid_height - 1)
            )

            # Check if position is free
            occupied = False
            for snake in self.state['snakes'].values():
                if pos in snake['positions']:
                    occupied = True
                    break

            if not occupied and pos not in self.state['food']:
                self.state['food'].append(pos)
                break

    async def user_action(self, user_id: str, action: Dict[str, Any]):
        """Handle user input (direction change)"""
        if action['type'] == 'join_game':
            await self._add_player(user_id)
        elif action['type'] == 'change_direction':
            await self._change_direction(user_id, action['direction'])
        elif action['type'] == 'start_game':
            if self.state['status'] == 'waiting':
                self.state['status'] = 'playing'

    async def _add_player(self, user_id: str):
        """Add player to game"""
        if user_id in self.state['snakes']:
            return

        # Find spawn position
        spawn_x = random.randint(2, self.grid_width - 3)
        spawn_y = random.randint(2, self.grid_height - 3)

        self.state['snakes'][user_id] = {
            'positions': [Position(spawn_x, spawn_y)],
            'direction': Direction.RIGHT,
            'alive': True,
        }
        self.state['scores'][user_id] = 0

        # Spawn initial food
        if not self.state['food']:
            for _ in range(3):
                self._spawn_food()

    async def _change_direction(self, user_id: str, direction_str: str):
        """Change snake direction"""
        if user_id not in self.state['snakes']:
            return

        try:
            new_direction = Direction[direction_str.upper()]
            snake = self.state['snakes'][user_id]

            # Prevent 180-degree turns
            current = snake['direction']
            if (new_direction.value[0] + current.value[0] == 0 and
                new_direction.value[1] + current.value[1] == 0):
                return

            snake['direction'] = new_direction
        except KeyError:
            pass

    async def get_state_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get current game state"""
        return {
            'type': 'snake_state',
            'state': self.state,
            'user_id': user_id,
        }

    async def _broadcast_state(self):
        """Send state to all connected users"""
        # This would be handled by the WebSocket manager
        pass
```

## 📺 YouTube Sync Implementation

### Simple Video Synchronization

```python
import time

class YouTubeSyncActivity(ActivityManager):
    def __init__(self, room_id: str, config: Dict = None):
        super().__init__(room_id)
        self.state = {
            'video_id': None,
            'current_time': 0.0,
            'is_playing': False,
            'playback_rate': 1.0,
            'last_action_time': time.time(),
            'master_user': None,  # User with control
        }

    async def start(self):
        """Start sync monitoring"""
        self.running = True
        self.task = asyncio.create_task(self._sync_loop())

    async def stop(self):
        """Stop sync"""
        self.running = False
        if self.task:
            self.task.cancel()

    async def _sync_loop(self):
        """Keep track of video time"""
        while self.running:
            if self.state['is_playing']:
                # Update current time based on elapsed time
                now = time.time()
                elapsed = now - self.state['last_action_time']
                self.state['current_time'] += elapsed * self.state['playback_rate']
                self.state['last_action_time'] = now

                # Broadcast current position every second
                await self._broadcast_sync()

            await asyncio.sleep(1.0)

    async def user_action(self, user_id: str, action: Dict[str, Any]):
        """Handle video control actions"""
        # Check if user has control permission
        if (self.state['master_user'] is not None and
            self.state['master_user'] != user_id):
            return  # Only master can control

        action_type = action['type']
        current_time = time.time()

        if action_type == 'load_video':
            self.state['video_id'] = action['video_id']
            self.state['current_time'] = 0.0
            self.state['is_playing'] = False

        elif action_type == 'play':
            self.state['is_playing'] = True
            self.state['last_action_time'] = current_time

        elif action_type == 'pause':
            # Update current time before pausing
            if self.state['is_playing']:
                elapsed = current_time - self.state['last_action_time']
                self.state['current_time'] += elapsed * self.state['playback_rate']
            self.state['is_playing'] = False
            self.state['last_action_time'] = current_time

        elif action_type == 'seek':
            self.state['current_time'] = action['time']
            self.state['last_action_time'] = current_time

        elif action_type == 'set_rate':
            # Update time before changing rate
            if self.state['is_playing']:
                elapsed = current_time - self.state['last_action_time']
                self.state['current_time'] += elapsed * self.state['playback_rate']
            self.state['playback_rate'] = action['rate']
            self.state['last_action_time'] = current_time

        # Broadcast change to all users
        await self._broadcast_sync()

    async def add_user(self, user_id: str, user_data: Dict[str, Any]):
        """Add user to video sync"""
        await super().add_user(user_id, user_data)

        # First user becomes master
        if self.state['master_user'] is None:
            self.state['master_user'] = user_id

    async def remove_user(self, user_id: str):
        """Remove user from sync"""
        await super().remove_user(user_id)

        # Transfer master control if needed
        if self.state['master_user'] == user_id:
            remaining_users = list(self.users.keys())
            self.state['master_user'] = remaining_users[0] if remaining_users else None

    async def get_state_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get current sync state"""
        # Calculate accurate current time
        current_time = self.state['current_time']
        if self.state['is_playing']:
            elapsed = time.time() - self.state['last_action_time']
            current_time += elapsed * self.state['playback_rate']

        return {
            'type': 'youtube_state',
            'video_id': self.state['video_id'],
            'current_time': current_time,
            'is_playing': self.state['is_playing'],
            'playback_rate': self.state['playback_rate'],
            'master_user': self.state['master_user'],
            'is_master': user_id == self.state['master_user'],
        }

    async def _broadcast_sync(self):
        """Broadcast sync state to all users"""
        # This would be handled by the WebSocket manager
        pass
```

## 🔌 WebSocket Integration

### Extended WebSocket Handler with Host Control

```python
from fastapi import WebSocket

class ExtendedConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.client_info: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, room: str, username: str):
        """Connect user and set as host if first in room"""
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = set()
            # First user becomes host
            await activity_registry.set_room_host(room, username)

        self.rooms[room].add(websocket)
        self.client_info[websocket] = {"room": room, "username": username}

        # Set default activity to chat if none exists
        if not activity_registry.get_room_activity(room):
            await activity_registry.change_room_activity(room, username, ActivityType.CHAT)

        # Send user role information
        role = activity_registry.get_user_role(room, username)
        await websocket.send_json({
            "type": "role_assigned",
            "role": role.value,
            "is_host": role == RoomRole.HOST
        })

    async def handle_activity_message(self, websocket: WebSocket, data: dict):
        """Route activity-specific messages"""
        client_info = self.client_info[websocket]
        room_id = client_info['room']
        user_id = client_info['username']

        message_type = data.get('type', '')

        # Handle activity change requests
        if message_type == 'change_activity':
            await self.handle_activity_change(websocket, data)
            return

        # Handle regular activity actions
        activity = activity_registry.get_room_activity(room_id)
        if not activity:
            return

        await activity.user_action(user_id, data)

        # Get updated state and broadcast
        state = await activity.get_state_for_user(user_id)
        await self.broadcast_to_room(room_id, state)

    async def handle_activity_change(self, websocket: WebSocket, data: dict):
        """Handle host changing room activity"""
        client_info = self.client_info[websocket]
        room_id = client_info['room']
        user_id = client_info['username']

        try:
            activity_type = ActivityType(data['activity_type'])
            config = data.get('config', {})

            success, message, activity = await activity_registry.change_room_activity(
                room_id, user_id, activity_type, config
            )

            if success:
                # Broadcast activity change to all room members
                await self.broadcast_to_room(room_id, {
                    "type": "activity_changed",
                    "activity_type": activity_type.value,
                    "activity_name": activity_type.display_name,
                    "changed_by": user_id,
                    "message": message
                })

                # Send initial state for new activity
                for ws in self.rooms[room_id]:
                    client = self.client_info[ws]
                    if activity:
                        state = await activity.get_state_for_user(client['username'])
                        await ws.send_json(state)
            else:
                # Send error back to requesting user
                await websocket.send_json({
                    "type": "activity_change_error",
                    "message": message
                })

        except ValueError:
            await websocket.send_json({
                "type": "activity_change_error",
                "message": "Invalid activity type"
            })

    async def get_room_info(self, room_id: str) -> dict:
        """Get room information including current activity and host"""
        activity = activity_registry.get_room_activity(room_id)
        host_id = activity_registry.room_hosts.get(room_id)

        return {
            "room_id": room_id,
            "current_activity": activity.activity_type.value if activity else None,
            "host": host_id,
            "available_activities": activity_registry.get_available_activities(),
            "user_count": len(self.rooms.get(room_id, set()))
        }

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await manager.connect(websocket, room, username)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get('type') in ['change_activity', 'get_room_info']:
                # Host control messages
                if data.get('type') == 'get_room_info':
                    room_info = await manager.get_room_info(room)
                    await websocket.send_json({
                        "type": "room_info",
                        **room_info
                    })
                else:
                    await manager.handle_activity_message(websocket, data)

            elif data.get('type', '').startswith('activity:'):
                # Activity-specific message
                await manager.handle_activity_message(websocket, data)
            else:
                # Regular chat message
                await manager.handle_chat_message(websocket, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

## 🎨 Frontend Activity Components

### Host Activity Control Panel

```tsx
// ActivitySwitcher.tsx
interface ActivitySwitcherProps {
  currentActivity: string;
  availableActivities: Array<{
    type: string;
    name: string;
    description: string;
  }>;
  isHost: boolean;
  onActivityChange: (activityType: string) => void;
}

function ActivitySwitcher({
  currentActivity,
  availableActivities,
  isHost,
  onActivityChange,
}: ActivitySwitcherProps) {
  const [showActivityMenu, setShowActivityMenu] = useState(false);

  const handleActivitySelect = (activityType: string) => {
    onActivityChange(activityType);
    setShowActivityMenu(false);
  };

  // Host control panel
  return (
    <div className="activity-switcher host-controls">
      <div className="current-activity">
        <span>
          Current:{" "}
          <strong>
            {availableActivities.find((a) => a.type === currentActivity)?.name}
          </strong>
        </span>
        <span className="host-badge">👑 HOST</span>
      </div>

      <div className="activity-controls">
        <button
          className="change-activity-btn"
          onClick={() => setShowActivityMenu(!showActivityMenu)}
        >
          🔄 Change Activity
        </button>

        {showActivityMenu && (
          <div className="activity-menu">
            <div className="menu-header">Select New Activity:</div>
            {availableActivities.map((activity) => (
              <button
                key={activity.type}
                className={`activity-option ${
                  currentActivity === activity.type ? "current" : ""
                }`}
                onClick={() => handleActivitySelect(activity.type)}
                disabled={currentActivity === activity.type}
              >
                <div className="activity-name">{activity.name}</div>
                <div className="activity-desc">{activity.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Usage in main App component
function App() {
  const [roomInfo, setRoomInfo] = useState(null);
  const [isHost, setIsHost] = useState(false);
  const { sendMessage } = useWebSocket();

  useEffect(() => {
    // Request room info when connected
    sendMessage({ type: "get_room_info" });
  }, []);

  const handleActivityChange = (activityType: string) => {
    sendMessage({
      type: "change_activity",
      activity_type: activityType,
      config: {}, // Optional configuration
    });
  };

  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case "role_assigned":
        setIsHost(message.is_host);
        break;

      case "room_info":
        setRoomInfo(message);
        break;

      case "activity_changed":
        // Show notification to all users
        showNotification(
          `Activity changed to ${message.activity_name} by ${message.changed_by}`
        );
        // Refresh room info
        sendMessage({ type: "get_room_info" });
        break;

      case "activity_change_error":
        showError(message.message);
        break;
    }
  };

  return (
    <div className="room-container">
      {roomInfo && (
        <ActivitySwitcher
          currentActivity={roomInfo.current_activity}
          availableActivities={roomInfo.available_activities}
          isHost={isHost}
          onActivityChange={handleActivityChange}
        />
      )}

      {/* Current activity component renders here */}
      <ActivityRenderer currentActivity={roomInfo?.current_activity} />
    </div>
  );
}
```

### Activity Switcher CSS

```css
.activity-switcher.host-controls {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.current-activity {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.host-badge {
  background: gold;
  color: black;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.change-activity-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.change-activity-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.activity-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  margin-top: 10px;
}

.menu-header {
  padding: 15px;
  border-bottom: 1px solid #eee;
  font-weight: bold;
  color: #333;
}

.activity-option {
  width: 100%;
  padding: 15px;
  border: none;
  text-align: left;
  background: white;
  cursor: pointer;
  transition: background 0.2s;
}

.activity-option:hover {
  background: #f5f5f5;
}

.activity-option.current {
  background: #e3f2fd;
  cursor: not-allowed;
}

.activity-name {
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.activity-desc {
  font-size: 14px;
  color: #666;
}

.activity-display {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #007bff;
  margin-bottom: 20px;
}

.host-notice {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}
```

### Snake Game Component

```tsx
// SnakeGame.tsx
function SnakeGame({ roomId }: { roomId: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameState, setGameState] = useState(null);
  const { sendMessage } = useWebSocket();

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      const directionMap = {
        ArrowUp: "UP",
        ArrowDown: "DOWN",
        ArrowLeft: "LEFT",
        ArrowRight: "RIGHT",
      };

      if (directionMap[e.key]) {
        sendMessage({
          type: "activity:snake:direction",
          direction: directionMap[e.key],
        });
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [sendMessage]);

  const joinGame = () => {
    sendMessage({ type: "activity:snake:join" });
  };

  const startGame = () => {
    sendMessage({ type: "activity:snake:start" });
  };

  return (
    <div className="snake-game">
      <div className="game-controls">
        <button onClick={joinGame}>Join Game</button>
        <button onClick={startGame}>Start Game</button>
      </div>
      <canvas
        ref={canvasRef}
        width={400}
        height={400}
        className="game-canvas"
      />
      <div className="game-info">Use arrow keys to control your snake!</div>
    </div>
  );
}
```

## 🚀 Benefits of This Approach

### Simplicity

- **Single Process**: No service discovery or network communication
- **Shared Memory**: Fast state access and updates
- **Direct Function Calls**: No serialization overhead
- **Easy Debugging**: Everything in one place

### Performance

- **Low Latency**: In-memory state updates
- **No Network Overhead**: Direct Python function calls
- **Efficient**: asyncio tasks share the same event loop
- **Scalable**: Can handle hundreds of concurrent rooms

### Development Speed

- **Fast Iteration**: Add new activities as simple classes
- **No Deployment Complexity**: Single container deployment
- **Easy Testing**: Unit test individual activity classes
- **Clear Code Flow**: Linear execution path

## 📈 Scaling When Needed

When you outgrow this simple approach:

1. **Add Redis**: Move state to Redis for persistence
2. **Horizontal Scaling**: Use Redis pub/sub for multi-instance sync
3. **Database**: Add PostgreSQL for long-term storage
4. **Load Balancer**: Sticky sessions for WebSocket connections

But start simple and scale only when you need to!

## 🎯 Implementation Plan

### Week 1: Core Infrastructure

- [ ] Activity manager base class
- [ ] Activity registry system
- [ ] Extended WebSocket handling
- [ ] Basic activity switching UI

### Week 2: Snake Game

- [ ] Snake game logic and collision detection
- [ ] Canvas renderer on frontend
- [ ] Input handling and real-time updates
- [ ] Score tracking and game over states

### Week 3: YouTube Sync

- [ ] YouTube API integration
- [ ] Time synchronization algorithm
- [ ] Master control system
- [ ] Custom video controls UI

### Week 4: Polish & Testing

- [ ] Error handling and reconnection
- [ ] UI/UX improvements
- [ ] Performance optimization
- [ ] Load testing with multiple rooms

**Total Time: 4 weeks to full prototype with 2 activities**

This approach gets you to a working prototype much faster than microservices, while still being well-architected and extensible!
