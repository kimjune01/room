import pytest
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestBasic:
    """Basic tests to verify test infrastructure."""

    @pytest.mark.unit
    def test_import_main(self):
        """Test that we can import the main module."""
        try:
            import main
            assert hasattr(main, 'ConnectionManager')
            assert hasattr(main, 'app')
        except ImportError as e:
            pytest.fail(f"Failed to import main module: {e}")

    @pytest.mark.unit
    def test_import_activities(self):
        """Test that we can import activity modules."""
        try:
            from activities.base import ActivityType
            from activities.youtube import YouTubeSyncActivity
            assert ActivityType.YOUTUBE is not None
            assert YouTubeSyncActivity is not None
        except ImportError as e:
            pytest.fail(f"Failed to import activity modules: {e}")

    @pytest.mark.unit
    def test_pytest_working(self):
        """Test that pytest is working correctly."""
        assert True
        assert 1 + 1 == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_pytest_working(self):
        """Test that async pytest is working correctly."""
        import asyncio
        await asyncio.sleep(0.001)
        assert True