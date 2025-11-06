# Room Activities System

A real-time multi-activity platform with WebSocket-powered rooms, built with React and Python FastAPI. Supports synchronized activities like multiplayer Snake game and YouTube watch parties.

## 🎯 What This Became

**From simple chat to rich activities.** This evolved into a platform supporting:
- Multi-user room-based activities
- Real-time synchronization across clients
- Activity switching with persistent state
- Host-controlled room management

## 🚀 Core Features

- **YouTube Watch Parties (Default)**: Rooms start with YouTube by default for instant video watching
- **Dark Theater Mode**: Immersive full-screen dark theme throughout the entire application
- **Real-Time Synchronization**: All users see the same state instantly
- **Host Permissions**: Room creators control activity switching and video playback
- **Multi-Room Activities**: Switch between YouTube sync, Snake game, and persistent chat
- **Persistent Chat**: Chat sidebar available across all activities

## 🛠️ Tech Stack

### Frontend
- **React 18.3+** with TypeScript for type safety
- **Vite 5+** for fast development and builds
- **WebSocket API** for real-time communication
- **YouTube IFrame API** for synchronized video playback
- **pnpm** as package manager

### Backend
- **Python 3.12+** with FastAPI
- **uvicorn** ASGI server with WebSocket support
- **Activity Manager pattern** for pluggable room activities
- **Server-authoritative state** for consistent synchronization

## 📋 Prerequisites

- Node.js 18+ and pnpm
- Python 3.12+

## 🔧 Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install fastapi uvicorn websockets
uvicorn main:app --reload --port 8001
```

### 2. Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

### 3. Open Browser

Navigate to `http://localhost:5173` to join rooms and start activities!

## 🏗️ Project Structure

```
.
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main room interface
│   │   ├── components/
│   │   │   ├── ActivitySwitcher.tsx   # Activity selection
│   │   │   ├── ActionDisplay.tsx      # User action notifications
│   │   │   ├── PersistentChat.tsx     # Chat sidebar
│   │   │   ├── SnakeActivity.tsx      # Snake game
│   │   │   ├── YouTubeActivity.tsx    # YouTube controls
│   │   │   └── YouTubePlayer.tsx      # IFrame API player
│   │   ├── utils/
│   │   │   └── debug-logger.ts        # Debug logging utility
│   │   └── types.ts                   # TypeScript definitions
│   └── package.json
├── backend/
│   ├── main.py                        # FastAPI + WebSocket server
│   ├── activities/
│   │   ├── base.py                    # Activity Manager pattern
│   │   ├── registry.py                # Activity registration
│   │   ├── snake.py                   # Snake game logic
│   │   └── youtube.py                 # YouTube sync logic
│   └── logs/                          # Debug logs (daily rotation)
│       └── debug-YYYY-MM-DD.log
├── tests/
│   ├── run_tests.py                   # Test runner
│   └── integration/                   # Integration tests
│       ├── test_youtube_sync.py       # YouTube synchronization
│       ├── test_new_user_sync.py      # New user behavior
│       └── test_basic_functionality.py
└── README.md
```

## 🚦 Running the System

```bash
# Terminal 1: Backend
cd backend && uvicorn main:app --reload --port 8001

# Terminal 2: Frontend
cd frontend && pnpm dev

# Browser
Open http://localhost:5173
```

## 🎮 Available Activities

### 🐍 Snake Game
- Multiplayer snake with real-time gameplay
- Join/leave at any time
- Collision detection and scoring
- Game state synchronization

### 📺 YouTube Watch Parties
- Synchronized video playback
- Master user controls (play/pause/seek/rate)
- Real-time sync across all viewers
- Buffering state management
- **Action Display**: Visual notifications above video showing latest user actions
- **Race Condition Protection**: Timestamp validation prevents stale state conflicts

### 💬 Persistent Chat
- Always-available chat sidebar
- Works across all activities
- User join/leave notifications

## 🔧 Current Limitations

- No user authentication (username-based)
- No message/state persistence
- Single-server deployment
- No rate limiting or abuse protection

## 🧪 Testing

Run all tests:

```bash
python tests/run_tests.py
```

Or run specific test suites:

```bash
python tests/integration/test_youtube_sync.py       # YouTube synchronization
python tests/integration/test_new_user_sync.py      # New user behavior
```

Test coverage includes:
- WebSocket connectivity and room management
- Host permissions and activity control
- YouTube video synchronization across clients
- New user sync behavior without disruption
- Multi-client real-time state synchronization

## 🐛 Debugging

The system includes comprehensive logging capabilities for debugging frontend issues:

### Debug Logger

The frontend automatically logs events to:
1. **Browser console** - Real-time debugging
2. **LocalStorage** - Persistent browser storage (last 50KB)
3. **Backend log files** - Daily rotating files in `backend/logs/`

### Using the Debug Logger

**In your frontend code:**
```typescript
import { DebugLogger } from './utils/debug-logger';

// Log events with optional data
DebugLogger.log('YouTube player ready', { videoId: 'abc123' });
DebugLogger.log('WebSocket message received', { type: 'state_update' });
```

**Access logs from browser console:**
```javascript
// View all logs
DebugLogger.getLogs()

// Download logs as file
DebugLogger.download()

// Clear logs
DebugLogger.clear()
```

### Backend Log Files

Logs are automatically saved to `backend/logs/debug-YYYY-MM-DD.log`:

```bash
# View today's logs
cat backend/logs/debug-2025-11-06.log

# Tail logs in real-time
tail -f backend/logs/debug-2025-11-06.log

# Get logs via API
curl http://localhost:8000/api/debug-logs
```

**Log format:**
```
[2025-11-06T16:41:50.000Z] YouTube player ready {"videoId": "abc123"}
[2025-11-06T16:42:15.123Z] WebSocket message received {"type": "state_update"}
```

### Debugging Tips

**API issues:**
```bash
# Test backend directly
curl -i http://localhost:8000/

# Test debug log endpoint
curl -X POST http://localhost:8000/api/debug-log \
  -H "Content-Type: application/json" \
  -d '{"message":"Test log","data":{"test":true}}'
```

**WebSocket issues:**
- Check browser console for connection errors
- Verify backend is running: `lsof -ti:8000`
- Check frontend proxy in `vite.config.ts`

**YouTube sync issues:**
- Look for `DebugLogger` entries in backend logs
- Check network tab for YouTube IFrame API loads
- Verify video ID format in logs

## 🚀 Next Steps

To extend the system:

1. **New Activities**: Add to `backend/activities/` following the ActivityManager pattern
2. **Authentication**: Add user accounts and room permissions
3. **Persistence**: Add database for user data and room history
4. **Scaling**: Add Redis for multi-server support
5. **Security**: Add rate limiting and input validation

## 📦 Key Dependencies

### Frontend
- React 18.3+ with TypeScript
- Vite for development
- YouTube IFrame API

### Backend
- FastAPI for WebSocket server
- uvicorn for ASGI serving
- asyncio for real-time game loops

## 🆕 Recent Improvements

### Dark Theater Mode (Latest)
- **Global Dark Theme**: Applied throughout the entire application by default
- **Theater Mode Styling**: YouTube video player triggers immersive full-screen dark layout
- **Custom Color Scheme**: Consistent dark colors with purple accents (Twitch-inspired)
- **Enhanced UI**: Custom scrollbars, borders, and text colors for seamless dark experience

### YouTube as Default Activity (Latest)
- **Instant Video Experience**: New rooms automatically start with YouTube activity
- **Streamlined Onboarding**: Users can immediately start watching videos upon joining
- **Backend & Frontend Sync**: Both server and client default to YouTube activity

### Action Display System
- **Visual Notifications**: User actions now appear above the YouTube video instead of in chat
- **Clean UI**: Shows "🎥 user loaded video", "▶️ user started playback", etc.
- **Persistent Display**: Actions stay visible until the next action occurs
- **TypeScript Integration**: Full type safety with YouTubeState interface updates

### Race Condition Fixes
- **Timestamp Validation**: Backend rejects stale state reports to prevent play/pause conflicts
- **Authoritative Flow**: Host actions take priority over delayed sync updates
- **Debug Logging**: Added stale report detection for easier troubleshooting
- **Client Timestamps**: Frontend includes precise timestamps in state reports

### Enhanced YouTube Sync
- **Improved Reliability**: Fixed race conditions that caused playback to quickly pause after resuming
- **Better State Management**: Last action tracking for seamless user experience
- **Cleaner Interface**: Removed YouTube action spam from chat system

## 🎯 Architecture Highlights

- **Activity Pattern**: Pluggable activities with consistent interface
- **Server Authority**: Backend maintains canonical state for synchronization
- **Real-time Sync**: WebSocket-based state updates across all clients
- **Host Model**: First user controls room activities and settings
- **Persistent Chat**: Chat available across all activities in sidebar

## 📝 Notes

This evolved from a simple chat prototype into a full multi-activity platform. The architecture supports:
- Adding new activities easily via the ActivityManager pattern
- Real-time synchronization with server-authoritative state
- Room-based isolation with host controls
- Comprehensive testing for reliability

Perfect for multiplayer experiences, virtual watch parties, and collaborative activities.

---

**Current Status**: Feature-complete for multi-activity rooms! 🎉