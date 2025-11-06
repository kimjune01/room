# Room-Based Activity Architecture

A comprehensive architectural guide for extending the WebSocket chat application to support multiple room activities including multiplayer games and synchronized video playback.

## 🎯 Vision

Transform each chat room into a versatile activity hub where users can engage in various real-time experiences:
- **Multiplayer Snake Game** with server-side game state
- **Synchronized YouTube Player** with shared playback control
- **Future Activities**: Drawing boards, polls, document collaboration, etc.

## 🏗️ Architectural Overview

### Core Principles (2024 Best Practices)

1. **Activity-Agnostic Rooms**: Rooms act as containers that can host any activity type
2. **Pluggable Activity System**: New activities can be added without modifying core room logic
3. **Server-Authoritative State**: All activity state is managed and validated server-side
4. **Event-Driven Communication**: Real-time updates via WebSocket events
5. **MACH Architecture**: Microservices, API-first, Cloud-native, Headless design

## 🔧 System Architecture

### High-Level Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   WebSocket     │    │   Activity      │
│   (React)       │◄──►│   Gateway       │◄──►│   Services      │
│                 │    │   (FastAPI)     │    │   (Microservice)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Room Manager  │    │   State Store   │
                       │   (Redis)       │    │   (Redis/DB)    │
                       └─────────────────┘    └─────────────────┘
```

### Activity Service Pattern

Each activity type is implemented as a separate microservice with standardized interfaces:

```python
# Activity Service Interface
class ActivityService:
    async def create_activity(self, room_id: str, config: dict) -> ActivityState
    async def join_activity(self, room_id: str, user_id: str) -> dict
    async def handle_action(self, room_id: str, user_id: str, action: dict) -> dict
    async def get_state(self, room_id: str) -> ActivityState
    async def leave_activity(self, room_id: str, user_id: str) -> dict
```

## 🎮 Activity #1: Multiplayer Snake Game

### Architecture Pattern: Server-Authoritative Game State

**Game State Management (2024 Best Practices)**:
- **Centralized State**: Server maintains authoritative game state
- **Client Prediction**: Clients predict movement for responsiveness
- **State Reconciliation**: Server validates and corrects client state
- **Tick-Based Updates**: Fixed timestep game loop (60fps recommended)

### Technical Implementation

```python
# Snake Game State Structure
class SnakeGameState:
    game_id: str
    status: GameStatus  # waiting, playing, finished
    players: Dict[str, Player]
    food_positions: List[Position]
    grid_size: Tuple[int, int]
    tick_rate: int = 10  # moves per second
    last_update: datetime
```

**WebSocket Event Flow**:
1. `snake:join` → Player joins game
2. `snake:move` → Player inputs direction
3. `snake:state` → Server broadcasts game state
4. `snake:collision` → Handle collisions
5. `snake:game_over` → Game end state

**State Synchronization Strategy**:
- **Full State Sync**: Every 1 second (reliability)
- **Delta Updates**: Every tick for movements (performance)
- **Event Reconciliation**: Handle disconnections gracefully

### Redis Storage Pattern

```json
{
  "game:snake:room123": {
    "state": "playing",
    "players": {...},
    "food": [...],
    "created_at": "2024-11-05T...",
    "last_tick": "2024-11-05T..."
  }
}
```

## 📺 Activity #2: Synchronized YouTube Player

### Architecture Pattern: Event-Driven State Synchronization

**Synchronization Challenges & Solutions**:
- **Network Latency**: Use server timestamps + client clock sync
- **Buffering Events**: Pause all when any client buffers
- **Seek Accuracy**: Server-side position reconciliation
- **Player Control**: Custom UI overlay (YouTube API limitations)

### Technical Implementation

```python
# YouTube Sync State Structure
class YouTubeSyncState:
    room_id: str
    video_id: str
    current_time: float
    is_playing: bool
    playback_rate: float
    last_action: ActionEvent
    server_timestamp: float
    connected_users: List[str]
```

**WebSocket Event Flow**:
1. `youtube:load` → Load new video
2. `youtube:play` → Start playback
3. `youtube:pause` → Pause playback
4. `youtube:seek` → Jump to time position
5. `youtube:sync` → Request current state
6. `youtube:buffer` → Handle buffering events

**Synchronization Algorithm**:
```python
def calculate_sync_position(server_time: float, last_action_time: float,
                          last_position: float, is_playing: bool) -> float:
    if not is_playing:
        return last_position

    elapsed = server_time - last_action_time
    return last_position + elapsed
```

### Custom Player Controls

Due to YouTube API limitations, implement custom control overlay:
- **Custom Progress Bar**: Sync-aware seeking
- **Master Control**: One user has control permissions
- **Buffer Management**: Auto-pause when any user buffers

## 🔌 Pluggable Activity System

### Activity Registration Pattern

```python
# Activity Registry
class ActivityRegistry:
    activities = {
        "chat": ChatActivity,
        "snake": SnakeGameActivity,
        "youtube": YouTubeSyncActivity,
        "whiteboard": WhiteboardActivity,  # Future
        "poll": PollActivity,              # Future
    }

    @classmethod
    def create_activity(cls, activity_type: str, room_id: str) -> ActivityService:
        if activity_type not in cls.activities:
            raise UnsupportedActivityError()
        return cls.activities[activity_type](room_id)
```

### Room Activity State Machine

```python
class RoomActivityState(Enum):
    EMPTY = "empty"           # No users
    CHAT_ONLY = "chat_only"   # Chat only
    ACTIVITY_LOBBY = "lobby"  # Choosing activity
    ACTIVITY_ACTIVE = "active" # Activity running
    ACTIVITY_PAUSED = "paused" # Activity paused
```

## 🚀 Implementation Strategy

### Phase 1: Core Infrastructure
1. **Activity Service Interface**: Define standard activity API
2. **Room State Management**: Extend current room manager
3. **Activity Registry**: Plugin system for activity types
4. **WebSocket Message Router**: Route activity-specific messages

### Phase 2: Snake Game Implementation
1. **Game Engine**: Server-side game logic with collision detection
2. **Client Renderer**: Canvas-based snake game UI
3. **Input Handling**: Direction commands via WebSocket
4. **State Synchronization**: Tick-based updates

### Phase 3: YouTube Sync Implementation
1. **YouTube API Integration**: Video loading and control
2. **Sync Engine**: Time-based synchronization algorithm
3. **Custom Controls**: Overlay UI for synchronized control
4. **Buffer Management**: Handle network variations

### Phase 4: Activity Switching
1. **Activity Selection UI**: Room activity picker
2. **State Persistence**: Save/restore activity states
3. **Seamless Transitions**: Switch between chat and activities

## 🔧 Technical Specifications

### Backend Extensions

```python
# Extended Room Manager
class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.activity_registry = ActivityRegistry()

    async def set_room_activity(self, room_id: str, activity_type: str):
        room = self.rooms[room_id]
        room.activity = self.activity_registry.create_activity(
            activity_type, room_id
        )
        await self.broadcast_activity_change(room_id, activity_type)
```

### Frontend Architecture

```tsx
// Activity Component Factory
const ActivityComponents = {
  chat: ChatComponent,
  snake: SnakeGameComponent,
  youtube: YouTubeSyncComponent,
};

function RoomComponent({ roomId }: { roomId: string }) {
  const [currentActivity, setCurrentActivity] = useState('chat');
  const ActivityComponent = ActivityComponents[currentActivity];

  return (
    <div className="room">
      <ActivitySelector onActivityChange={setCurrentActivity} />
      <ActivityComponent roomId={roomId} />
    </div>
  );
}
```

## 📈 Scalability Considerations

### Horizontal Scaling (2024 Patterns)

1. **Service Mesh**: Istio/Linkerd for inter-service communication
2. **Activity Sharding**: Distribute activities across service instances
3. **Redis Clustering**: Partition room state across Redis cluster
4. **Auto-scaling**: Kubernetes HPA based on room count/activity

### Performance Optimizations

1. **State Compression**: Gzip WebSocket messages for large states
2. **Delta Synchronization**: Send only changed state portions
3. **Connection Pooling**: Reuse WebSocket connections efficiently
4. **Caching Strategy**: Redis for hot activity states

### Monitoring & Observability

```python
# Activity Metrics
class ActivityMetrics:
    - rooms_active_by_type
    - average_users_per_room
    - message_throughput_by_activity
    - game_session_duration
    - video_sync_accuracy
    - connection_stability
```

## 🔮 Future Activity Ideas

- **Collaborative Whiteboard**: Real-time drawing with conflict resolution
- **Live Polls**: Instant voting with real-time results
- **Code Editor**: Collaborative programming with syntax highlighting
- **Music Sync**: Spotify/Apple Music synchronized playback
- **Virtual Meeting**: Video chat integration
- **Document Collaboration**: Real-time text editing
- **Virtual Poker**: Card game with server-side deck management

## 📋 Implementation Checklist

### Infrastructure
- [ ] Activity service interface definition
- [ ] Extended room manager with activity support
- [ ] WebSocket message routing for activities
- [ ] Redis schema for activity state storage
- [ ] Activity registry and plugin system

### Snake Game
- [ ] Server-side game engine with collision detection
- [ ] Canvas-based client renderer
- [ ] Input handling and command queue
- [ ] Tick-based state synchronization
- [ ] Game state persistence and replay

### YouTube Sync
- [ ] YouTube API integration and video loading
- [ ] Server timestamp synchronization
- [ ] Custom control overlay implementation
- [ ] Buffer detection and handling
- [ ] Master control permission system

### General
- [ ] Activity selection UI components
- [ ] State transition animations
- [ ] Error handling and reconnection logic
- [ ] Performance monitoring and metrics
- [ ] Documentation and deployment guides

## 🎯 Success Metrics

- **Technical**: <100ms activity state sync latency
- **User Experience**: 95%+ activity session completion rate
- **Scalability**: Support 1000+ concurrent rooms
- **Reliability**: 99.9% activity uptime
- **Performance**: <5MB memory per active room

---

This architecture enables rapid development of new room activities while maintaining performance, scalability, and maintainability. The pluggable design allows for experimentation with new activity types without disrupting the core chat functionality.