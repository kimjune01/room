import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
import websockets
from fastapi.testclient import TestClient

from main import app, manager, ConnectionManager
from activities.base import ActivityType
from activities.youtube import YouTubeSyncActivity


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest_asyncio.fixture
async def clean_manager() -> AsyncGenerator[ConnectionManager, None]:
    """Create a clean ConnectionManager instance for testing."""
    test_manager = ConnectionManager()
    yield test_manager

    # Cleanup: stop all activities and clear state
    for activity in list(test_manager.room_activities.values()):
        try:
            await activity.stop()
        except:
            pass

    test_manager.rooms.clear()
    test_manager.client_info.clear()
    test_manager.room_hosts.clear()
    test_manager.room_activities.clear()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_websockets(mock_websocket):
    """Create multiple mock WebSockets for multi-user testing."""
    def create_mock_ws(name: str):
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_text = AsyncMock()
        ws.close = AsyncMock()
        ws._test_name = name  # For debugging
        return ws

    return {
        'host': create_mock_ws('host'),
        'guest1': create_mock_ws('guest1'),
        'guest2': create_mock_ws('guest2'),
        'guest3': create_mock_ws('guest3')
    }


@pytest_asyncio.fixture
async def youtube_activity(clean_manager) -> AsyncGenerator[YouTubeSyncActivity, None]:
    """Create a YouTube activity for testing."""
    room_id = "test_room"
    activity = YouTubeSyncActivity(room_id)

    # Set up message handler
    async def mock_handler(room: str, message: dict, exclude_user: str = None, target_user: str = None):
        pass

    activity.set_message_handler(mock_handler)
    await activity.start()

    yield activity

    try:
        await activity.stop()
    except:
        pass


@pytest.fixture
def sample_video_data():
    """Sample YouTube video data for testing."""
    return {
        'video_id': 'dQw4w9WgXcQ',
        'current_time': 10.5,
        'is_playing': True,
        'playback_rate': 1.0
    }


@pytest.fixture
def sample_users():
    """Sample user data for testing."""
    return {
        'host': 'TestHost',
        'guest1': 'TestGuest1',
        'guest2': 'TestGuest2'
    }


class AsyncContextManager:
    """Helper for async context management in tests."""
    def __init__(self, async_func, *args, **kwargs):
        self.async_func = async_func
        self.args = args
        self.kwargs = kwargs
        self.result = None

    async def __aenter__(self):
        self.result = await self.async_func(*self.args, **self.kwargs)
        return self.result

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.result, 'close'):
            await self.result.close()


@pytest.fixture
def async_context():
    """Helper fixture for async context management."""
    return AsyncContextManager