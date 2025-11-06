import { useEffect, useRef } from 'react';
import type { SnakeState, SnakePosition, SnakeAction } from '../types';

interface SnakeActivityProps {
  state: SnakeState;
  config: {
    grid_width: number;
    grid_height: number;
    tick_rate: number;
    max_players: number;
  };
  isPlayer: boolean;
  onAction: (action: SnakeAction) => void;
}

export function SnakeActivity({ state, config, isPlayer, onAction }: SnakeActivityProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cellSize = 20;
  const canvasWidth = config.grid_width * cellSize;
  const canvasHeight = config.grid_height * cellSize;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Draw grid
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let x = 0; x <= config.grid_width; x++) {
      ctx.beginPath();
      ctx.moveTo(x * cellSize, 0);
      ctx.lineTo(x * cellSize, canvasHeight);
      ctx.stroke();
    }
    for (let y = 0; y <= config.grid_height; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * cellSize);
      ctx.lineTo(canvasWidth, y * cellSize);
      ctx.stroke();
    }

    // Draw food
    ctx.fillStyle = '#f44336';
    state.food?.forEach((food: SnakePosition) => {
      ctx.fillRect(
        food.x * cellSize + 2,
        food.y * cellSize + 2,
        cellSize - 4,
        cellSize - 4
      );
    });

    // Draw snakes
    const colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336', '#00BCD4', '#FFEB3B', '#795548'];
    let colorIndex = 0;

    Object.entries(state.players || {}).forEach(([, player]) => {
      const color = colors[colorIndex % colors.length];
      ctx.fillStyle = player.alive ? color : '#666';
      
      player.positions?.forEach((pos: SnakePosition, index: number) => {
        const alpha = player.alive ? (index === 0 ? 1 : 0.7) : 0.3;
        ctx.globalAlpha = alpha;
        ctx.fillRect(
          pos.x * cellSize + 1,
          pos.y * cellSize + 1,
          cellSize - 2,
          cellSize - 2
        );
      });
      
      ctx.globalAlpha = 1;
      colorIndex++;
    });
  }, [state, config, canvasWidth, canvasHeight]);

  useEffect(() => {
    if (!isPlayer || state.status !== 'playing') return;

    const handleKeyPress = (e: KeyboardEvent) => {
      let direction = '';
      switch (e.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
          direction = 'UP';
          break;
        case 'ArrowDown':
        case 's':
        case 'S':
          direction = 'DOWN';
          break;
        case 'ArrowLeft':
        case 'a':
        case 'A':
          direction = 'LEFT';
          break;
        case 'ArrowRight':
        case 'd':
        case 'D':
          direction = 'RIGHT';
          break;
        default:
          return;
      }

      e.preventDefault();
      onAction({
        type: 'activity:snake:change_direction',
        direction
      });
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isPlayer, state.status, onAction]);

  const joinGame = () => {
    onAction({ type: 'activity:snake:join_game' });
  };

  const startGame = () => {
    onAction({ type: 'activity:snake:start_game' });
  };

  const restartGame = () => {
    onAction({ type: 'activity:snake:restart_game' });
  };

  const playerCount = Object.keys(state.players || {}).length;
  const aliveCount = Object.values(state.players || {}).filter(p => p.alive).length;

  return (
    <div className="snake-activity">
      <div className="snake-info">
        <h3>Snake Game</h3>
        <p>Status: <strong>{state.status}</strong></p>
        <p>Players: {playerCount}/{config.max_players}</p>
        {state.status === 'playing' && <p>Alive: {aliveCount}</p>}
        {state.winner && <p>Winner: <strong>{state.winner}</strong></p>}
      </div>

      <div className="snake-canvas-container">
        <canvas
          ref={canvasRef}
          width={canvasWidth}
          height={canvasHeight}
          className="snake-canvas"
        />
      </div>

      <div className="snake-controls">
        {!isPlayer && state.status === 'waiting' && (
          <button onClick={joinGame} className="join-btn">
            Join Game
          </button>
        )}
        
        {state.status === 'waiting' && playerCount > 0 && (
          <button onClick={startGame} className="start-btn">
            Start Game
          </button>
        )}
        
        {state.status === 'finished' && (
          <button onClick={restartGame} className="restart-btn">
            Restart Game
          </button>
        )}
      </div>

      {isPlayer && state.status === 'playing' && (
        <div className="snake-instructions">
          <p>Use WASD or Arrow Keys to move</p>
        </div>
      )}

      {Object.keys(state.players || {}).length > 0 && (
        <div className="snake-scoreboard">
          <h4>Scoreboard</h4>
          {Object.entries(state.players || {}).map(([playerId, player]) => (
            <div key={playerId} className={`score-entry ${!player.alive ? 'dead' : ''}`}>
              <span className="player-name">{playerId}</span>
              <span className="player-score">Score: {player.score}</span>
              <span className="player-status">{player.alive ? '🐍' : '💀'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}