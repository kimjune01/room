# Room

Real-time synchronized YouTube watching and multiplayer activities.

## Features

- **YouTube Watch Parties** - Synchronized video playback with host controls (default activity)
- **Dark Theater Mode** - Immersive dark UI throughout the application
- **Multiplayer Snake** - Real-time multiplayer game
- **Persistent Chat** - Always-visible chat sidebar
- **Host Controls** - Room creator manages activities and playback

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Frontend (new terminal)
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:5173

## Tech Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python + FastAPI + WebSockets
- **Activities**: YouTube IFrame API, Canvas-based Snake game


## Recent Updates

- **Dark theater mode** throughout the application
- **YouTube as default** activity for new rooms
- Synchronized playback with host controls
- Visual action notifications above video
- Fixed race conditions in state synchronization

## License

MIT