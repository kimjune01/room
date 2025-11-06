# Codebase Index

> Real-Time Chat Room Application with Host Controls
>
> **Quick Stats:** Backend: 156 lines | Frontend: 203 lines | Test Coverage: 5 test suites

## Project Overview

A production-ready WebSocket-based chat room application with multi-room support, user identity, and host-based permission system. Built with FastAPI (backend) and React 19 + TypeScript + Vite (frontend).

---

## Directory Structure

```
room/
├── backend/               # FastAPI WebSocket server
│   ├── main.py           # Single-file backend (156 lines)
│   ├── requirements.txt  # Python dependencies
│   └── .venv/           # Virtual environment
│
├── frontend/             # React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx      # Main chat component (203 lines)
│   │   ├── App.css      # Component styles
│   │   ├── main.tsx     # React entry point
│   │   ├── index.css    # Global styles
│   │   └── assets/      # Static assets
│   ├── public/          # Public assets
│   ├── index.html       # HTML entry point
│   ├── package.json     # Node dependencies
│   ├── vite.config.ts   # Vite configuration
│   └── tsconfig*.json   # TypeScript configs
│
├── test_*.py            # Test suites (5 files)
├── *.md                 # Documentation (5 files)
└── .claude/             # Claude Code configuration
```

---

## Backend Reference

### Main File: `backend/main.py`

**Location:** `/Users/junekim/Documents/room/backend/main.py`

#### ConnectionManager Class (lines 18-85)

**Key Data Structures:**
- `rooms: Dict[str, Set[WebSocket]]` - Room → connections mapping
- `client_info: Dict[WebSocket, Dict]` - WebSocket → user info
- `room_hosts: Dict[str, str]` - Room → host username
- `room_host_state: Dict[str, Dict]` - Room → host state (title, etc.)

**Key Methods:**
| Method | Lines | Purpose |
|--------|-------|---------|
| `connect()` | 31-48 | Accept WebSocket, assign host if first in room |
| `disconnect()` | 50-63 | Remove client, cleanup empty rooms |
| `is_host()` | 65-72 | Check if user is room host |
| `broadcast_to_room()` | 74-85 | Send message to all room members |

#### API Endpoints

| Method | Path | Purpose | Line |
|--------|------|---------|------|
| GET | `/` | Health check | 96-98 |
| WS | `/ws/{room}/{username}` | Connect to room | 101-155 |

#### WebSocket Message Types

| Type | Direction | Purpose | Handler Line |
|------|-----------|---------|--------------|
| `update_host_state` | Client → Server | Host updates room settings | 135-147 |
| `message` | Client → Server | Chat message | 149-155 |
| `user_joined` | Server → Client | User join notification | 110-115 |
| `user_left` | Server → Client | User leave notification | 118-125 |
| `host_state_update` | Server → Client | Broadcast host state changes | 144-147 |
| `error` | Server → Client | Permission/validation errors | 140-142 |

#### Dependencies: `backend/requirements.txt`

```
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
websockets>=12.0
python-multipart>=0.0.9
```

---

## Frontend Reference

### Main Files

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/index.html` | - | HTML shell |
| `frontend/src/main.tsx` | - | React 19 entry point |
| `frontend/src/App.tsx` | 203 | Main chat component |
| `frontend/src/App.css` | - | Component styles |
| `frontend/src/index.css` | - | Global styles + dark mode |

### App Component: `frontend/src/App.tsx`

**Location:** `/Users/junekim/Documents/room/frontend/src/App.tsx`

#### State Management

```typescript
const [room, setRoom] = useState<string>('')              // Current room
const [username, setUsername] = useState<string>('')       // User identity
const [connected, setConnected] = useState<boolean>(false) // WS status
const [messages, setMessages] = useState<Message[]>([])    // Chat history
const [inputMessage, setInputMessage] = useState<string>('')
const [host, setHost] = useState<string>('')               // Room host
const [hostState, setHostState] = useState<HostState>({    // Host state
  title: ''
})
const [isEditingTitle, setIsEditingTitle] = useState(false)
const [editedTitle, setEditedTitle] = useState('')
const wsRef = useRef<WebSocket | null>(null)
```

#### TypeScript Interfaces

```typescript
interface Message {
  type: 'message' | 'user_joined' | 'user_left' | 'host_state_update' | 'error'
  username: string
  message: string
  own_message?: boolean
  host_state?: HostState
  host?: string
}

interface HostState {
  title: string
}
```

#### Key Functions

| Function | Purpose | Line Range |
|----------|---------|------------|
| `connect()` | Establish WebSocket, handle messages | ~50-90 |
| `disconnect()` | Close WebSocket connection | ~92-98 |
| `sendMessage()` | Send chat message | ~100-115 |
| `updateRoomTitle()` | Host-only title update | ~117-130 |
| `startEditingTitle()` | Enter title edit mode | ~132-135 |

#### UI States

1. **Pre-connection (Login):**
   - Room name input
   - Username input
   - Connect button

2. **Connected (Chat):**
   - Room title with host badge
   - Edit title button (host only)
   - Message list with auto-scroll
   - Message input + Send button
   - Disconnect button

#### Message Rendering Styles

| Message Type | Style | Alignment |
|--------------|-------|-----------|
| Own messages | Blue background | Right |
| Other messages | Gray background | Left |
| System messages | Yellow background | Center |

### Frontend Configuration

**`frontend/package.json`** - Dependencies:
```json
{
  "dependencies": {
    "react": "^19.1.1",
    "react-dom": "^19.1.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.0.4",
    "typescript": "~5.9.3",
    "vite": "^7.1.7",
    "eslint": "^9.36.0"
  }
}
```

**Scripts:**
- `pnpm dev` - Start dev server (port 5173)
- `pnpm build` - Production build
- `pnpm lint` - Run ESLint
- `pnpm preview` - Preview production build

---

## Tests

### Test Files (Project Root)

| File | Lines | Purpose |
|------|-------|---------|
| `test_smoke.py` | 286 | **Main test suite** - comprehensive smoke tests |
| `test_roundtrip_simple.py` | 97 | Two-client message exchange test |
| `test_roundtrip.py` | - | Earlier round-trip test version |
| `test_host_state.py` | - | Host state management tests |
| `test_host_permissions.py` | - | Host permission validation tests |
| `test_e2e_activities.py` | - | Future activity system tests |

### Running Tests

```bash
# Run comprehensive smoke tests
python test_smoke.py

# Run simple round-trip test
python test_roundtrip_simple.py

# Run specific test
python test_host_state.py
```

### TestClient Helper (in test_smoke.py)

Reusable WebSocket test client with async support:
```python
client = TestClient(room="test-room", username="Alice")
await client.connect()
await client.send_message("Hello")
messages = await client.receive_messages(count=2, timeout=2.0)
await client.disconnect()
```

---

## Documentation

| File | Lines | Purpose |
|------|-------|---------|
| `README.md` | 186 | Quick start guide, philosophy, limitations |
| `IMPLEMENTATION_SUMMARY.md` | 103 | Build summary, features, time to delivery |
| `ROOM_ACTIVITIES_ARCHITECTURE.md` | 334 | Future vision: microservices architecture |
| `SIMPLE_ACTIVITIES_ARCHITECTURE.md` | 1027 | Alternative future: simple single-process design |
| `test_manual_instructions.md` | - | Manual testing procedures |
| `index.md` | - | **This file** - codebase reference |

---

## Quick Reference

### Running the Application

**Backend:**
```bash
cd backend
source .venv/bin/activate  # or: uv venv && source .venv/bin/activate
uvicorn main:app --reload
# Runs on http://localhost:8000
```

**Frontend:**
```bash
cd frontend
pnpm dev
# Runs on http://localhost:5173
```

### WebSocket Connection

**URL Format:** `ws://localhost:8000/ws/{room}/{username}`

**Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/my-room/Alice')
```

### Sending Messages

**Chat Message:**
```json
{
  "type": "message",
  "message": "Hello, world!"
}
```

**Update Room Title (Host Only):**
```json
{
  "type": "update_host_state",
  "host_state": {
    "title": "New Room Title"
  }
}
```

### Key Features Implemented

1. ✅ Multi-room support
2. ✅ User identity (username-based)
3. ✅ Real-time messaging via WebSocket
4. ✅ Message echo (sender sees own messages)
5. ✅ Host system (first user = host)
6. ✅ Host controls (room title editing)
7. ✅ Permission system (server-side validation)
8. ✅ Join/leave notifications
9. ✅ Room cleanup (empty rooms auto-deleted)
10. ✅ Error handling (graceful disconnection)

### Architecture Patterns

**Backend:**
- Single-file FastAPI application
- In-memory state management
- Room-based connection pooling
- Broadcast messaging pattern
- Server-side permission validation

**Frontend:**
- React hooks for state management
- `useRef` for persistent WebSocket
- Conditional rendering for UI states
- Optimistic UI with server confirmation
- TypeScript for type safety

**Communication:**
- WebSocket for bidirectional real-time
- JSON message format
- Type-based message routing
- Echo pattern for message confirmation

---

## Future Extensions

See architecture documents for detailed plans:

1. **Multiplayer Activities** (Snake game, etc.)
   - See: `ROOM_ACTIVITIES_ARCHITECTURE.md` (microservices)
   - Or: `SIMPLE_ACTIVITIES_ARCHITECTURE.md` (single-process)

2. **YouTube Sync** (synchronized video playback)
   - Host controls playback
   - Real-time state synchronization

3. **Additional Host Controls**
   - User roles and permissions
   - Kick/ban functionality
   - Room settings management

---

## Development Preferences (from .claude/CLAUDE.md)

- Python: use `uv`
- React/TypeScript: use `Vite`
- Package manager: use `pnpm` (not npm)
- Git: auto-accept non-destructive commands
- Always verify solutions work (test/build/run)
- TDD approach: write tests first

---

## Troubleshooting

### Connection Issues

1. **Backend not responding:**
   ```bash
   lsof -ti:8000  # Check if port 8000 is in use
   ```

2. **Frontend can't connect:**
   - Verify backend is running on port 8000
   - Check WebSocket URL in browser console
   - Ensure no CORS issues (CORS configured for localhost:5173)

3. **Messages not appearing:**
   - Check browser console for WebSocket errors
   - Verify JSON message format
   - Check backend logs for exceptions

### Common Debug Commands

```bash
# Check running ports
lsof -ti:8000 && lsof -ti:5173

# Test backend directly
curl -i http://localhost:8000/

# Test WebSocket (requires websocat or similar)
websocat ws://localhost:8000/ws/test-room/TestUser
```

---

## File Locations Quick Reference

### Backend
- Main server: `backend/main.py`
- Dependencies: `backend/requirements.txt`
- Venv: `backend/.venv/`

### Frontend
- Main component: `frontend/src/App.tsx`
- Entry point: `frontend/src/main.tsx`
- HTML shell: `frontend/index.html`
- Styles: `frontend/src/App.css`, `frontend/src/index.css`
- Config: `frontend/vite.config.ts`, `frontend/package.json`

### Tests
- All test files in project root: `test_*.py`

### Documentation
- All docs in project root: `*.md`

---

**Last Updated:** 2025-11-05
**Project Status:** Production-ready prototype with test coverage
