import asyncio
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any
from .base import ActivityManager, ActivityType

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

@dataclass
class Position:
    x: int
    y: int

    def __eq__(self, other):
        return isinstance(other, Position) and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

class SnakePlayer:
    def __init__(self, user_id: str, start_pos: Position):
        self.user_id = user_id
        self.positions = [start_pos]
        self.direction = Direction.RIGHT
        self.alive = True
        self.score = 0

class SnakeGameActivity(ActivityManager):
    def __init__(self, room_id: str, config: Dict[str, Any] = None):
        super().__init__(room_id, ActivityType.SNAKE)

        config = config or {}
        self.grid_width = config.get('grid_width', 20)
        self.grid_height = config.get('grid_height', 20)
        self.tick_rate = config.get('tick_rate', 10)  # ticks per second
        self.max_players = config.get('max_players', 8)

        self.state = {
            'status': 'waiting',  # waiting, playing, finished
            'players': {},        # user_id -> SnakePlayer
            'food': [],          # list of food positions
            'tick_count': 0,
            'winner': None
        }

        self.players: Dict[str, SnakePlayer] = {}
        self.food_positions: List[Position] = []

    async def start(self):
        """Start the snake game"""
        await super().start()
        self.task = asyncio.create_task(self._game_loop())
        print(f"Snake game started for room {self.room_id}")

    async def stop(self):
        """Stop the snake game"""
        await super().stop()
        print(f"Snake game stopped for room {self.room_id}")

    async def _game_loop(self):
        """Main game simulation loop"""
        while self.running:
            if self.state['status'] == 'playing':
                await self._update_game_state()
                await self._broadcast_game_state()

            # Sleep for tick interval
            await asyncio.sleep(1.0 / self.tick_rate)

    async def _update_game_state(self):
        """Update game state for one tick"""
        self.state['tick_count'] += 1

        # Move all alive snakes
        for user_id, player in self.players.items():
            if not player.alive:
                continue

            # Calculate new head position
            head = player.positions[0]
            dx, dy = player.direction.value
            new_head = Position(head.x + dx, head.y + dy)

            # Check wall collision
            if (new_head.x < 0 or new_head.x >= self.grid_width or
                new_head.y < 0 or new_head.y >= self.grid_height):
                player.alive = False
                continue

            # Check self collision
            if new_head in player.positions:
                player.alive = False
                continue

            # Check collision with other snakes
            collision = False
            for other_id, other_player in self.players.items():
                if other_id != user_id and new_head in other_player.positions:
                    player.alive = False
                    collision = True
                    break

            if collision:
                continue

            # Move snake
            player.positions.insert(0, new_head)

            # Check food collision
            if new_head in self.food_positions:
                self.food_positions.remove(new_head)
                player.score += 1
                self._spawn_food()
            else:
                # Remove tail if no food eaten
                player.positions.pop()

        # Check game end conditions
        alive_players = [p for p in self.players.values() if p.alive]
        if len(alive_players) <= 1 and len(self.players) > 1:
            self.state['status'] = 'finished'
            if alive_players:
                self.state['winner'] = alive_players[0].user_id

        # Update state for broadcasting
        self.state['players'] = {
            user_id: {
                'positions': [{'x': pos.x, 'y': pos.y} for pos in player.positions],
                'direction': player.direction.name,
                'alive': player.alive,
                'score': player.score
            }
            for user_id, player in self.players.items()
        }

        self.state['food'] = [{'x': food.x, 'y': food.y} for food in self.food_positions]

    def _spawn_food(self):
        """Spawn food at random position"""
        attempts = 0
        while attempts < 100:  # Prevent infinite loop
            pos = Position(
                random.randint(0, self.grid_width - 1),
                random.randint(0, self.grid_height - 1)
            )

            # Check if position is free
            occupied = False
            for player in self.players.values():
                if pos in player.positions:
                    occupied = True
                    break

            if not occupied and pos not in self.food_positions:
                self.food_positions.append(pos)
                break

            attempts += 1

    async def _broadcast_game_state(self):
        """Broadcast current game state to all players"""
        await self.broadcast_to_room({
            "type": "snake_state",
            "state": self.state
        })

    async def user_action(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user input"""
        action_type = action.get("type", "").replace("activity:snake:", "")

        if action_type == "join_game":
            return await self._handle_join_game(user_id)
        elif action_type == "change_direction":
            return await self._handle_change_direction(user_id, action)
        elif action_type == "start_game":
            return await self._handle_start_game(user_id)
        elif action_type == "restart_game":
            return await self._handle_restart_game(user_id)

        return {"type": "error", "message": f"Unknown snake action: {action_type}"}

    async def _handle_join_game(self, user_id: str) -> Dict[str, Any]:
        """Handle player joining the game"""
        if user_id in self.players:
            return {"type": "error", "message": "Already in game"}

        if len(self.players) >= self.max_players:
            return {"type": "error", "message": "Game is full"}

        # Find spawn position
        spawn_x = random.randint(2, self.grid_width - 3)
        spawn_y = random.randint(2, self.grid_height - 3)
        start_pos = Position(spawn_x, spawn_y)

        # Create new player
        player = SnakePlayer(user_id, start_pos)
        self.players[user_id] = player

        # Spawn initial food if first player
        if len(self.players) == 1:
            for _ in range(3):
                self._spawn_food()

        await self.broadcast_to_room({
            "type": "snake_player_joined",
            "user_id": user_id,
            "player_count": len(self.players)
        })

        return {"type": "snake_joined", "message": "Joined snake game"}

    async def _handle_change_direction(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle direction change"""
        if user_id not in self.players:
            return {"type": "error", "message": "Not in game"}

        direction_str = action.get("direction", "").upper()
        try:
            new_direction = Direction[direction_str]
            player = self.players[user_id]

            # Prevent 180-degree turns
            current = player.direction
            if (new_direction.value[0] + current.value[0] == 0 and
                new_direction.value[1] + current.value[1] == 0):
                return {"type": "error", "message": "Cannot reverse direction"}

            player.direction = new_direction
            return {"type": "snake_direction_changed", "direction": direction_str}

        except KeyError:
            return {"type": "error", "message": f"Invalid direction: {direction_str}"}

    async def _handle_start_game(self, user_id: str) -> Dict[str, Any]:
        """Handle starting the game"""
        if self.state['status'] != 'waiting':
            return {"type": "error", "message": "Game already started or finished"}

        if len(self.players) < 1:
            return {"type": "error", "message": "Need at least 1 player"}

        self.state['status'] = 'playing'

        await self.broadcast_to_room({
            "type": "snake_game_started",
            "player_count": len(self.players)
        })

        return {"type": "snake_game_started", "message": "Game started"}

    async def _handle_restart_game(self, user_id: str) -> Dict[str, Any]:
        """Handle restarting the game"""
        # Reset game state
        self.state = {
            'status': 'waiting',
            'players': {},
            'food': [],
            'tick_count': 0,
            'winner': None
        }

        # Reset all players
        for player in self.players.values():
            # Reset to starting position
            spawn_x = random.randint(2, self.grid_width - 3)
            spawn_y = random.randint(2, self.grid_height - 3)
            player.positions = [Position(spawn_x, spawn_y)]
            player.direction = Direction.RIGHT
            player.alive = True
            player.score = 0

        # Reset food
        self.food_positions = []
        for _ in range(3):
            self._spawn_food()

        await self.broadcast_to_room({
            "type": "snake_game_restarted"
        })

        return {"type": "snake_game_restarted", "message": "Game restarted"}

    async def add_user(self, user_id: str):
        """Add user to activity"""
        await super().add_user(user_id)

    async def remove_user(self, user_id: str):
        """Remove user from activity"""
        await super().remove_user(user_id)

        # Remove from game if playing
        if user_id in self.players:
            del self.players[user_id]

            await self.broadcast_to_room({
                "type": "snake_player_left",
                "user_id": user_id,
                "player_count": len(self.players)
            })

    async def get_state_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get current game state for user"""
        return {
            "type": "activity_state",
            "activity_type": self.activity_type.value,
            "activity_name": self.activity_type.display_name,
            "state": self.state,
            "is_player": user_id in self.players,
            "users": list(self.users),
            "config": {
                "grid_width": self.grid_width,
                "grid_height": self.grid_height,
                "tick_rate": self.tick_rate,
                "max_players": self.max_players
            }
        }