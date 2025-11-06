import { useState, useEffect } from 'react';
// Using Tailwind CSS classes instead of external CSS
import type { Message, ActivityState, WebSocketMessage, YouTubeStateUpdate, YouTubeState, SnakeActivityState, YouTubeActivityState } from './types';
import { ActivitySwitcher } from './components/ActivitySwitcher';
import { PersistentChat } from './components/PersistentChat';
import { SnakeActivity } from './components/SnakeActivity';
import { YouTubeActivity } from './components/YouTubeActivity';
import { DebugLogger } from './utils/debug-logger';
import { useAppStore } from './store/useAppStore';

function App() {
  // Get state and actions from Zustand store
  const {
    room, setRoom,
    username, setUsername,
    connected, setConnected,
    messages, addMessage,
    isHost, setIsHost,
    host, setHost,
    activities, setActivities,
    currentActivity, setCurrentActivity,
    wsRef, setWsRef,
    sendMessage,
    changeActivity,
    sendActivityAction
  } = useAppStore();

  // Keep playback-specific state as local state (excluding from Zustand)
  const [activityState, setActivityState] = useState<ActivityState | null>(null);
  const [youtubePlayerStatus, setYoutubePlayerStatus] = useState<{isAPIReady: boolean, isPlayerReady: boolean} | null>(null);

  const connect = () => {
    if (!username || !room) return;

    const ws = new WebSocket(`ws://localhost:8001/ws/${room}/${username}`);

    ws.onopen = () => {
      console.log('Connected to WebSocket');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as WebSocketMessage;
      console.log('Received message:', message);

      if (message.type === 'role_assigned') {
        setIsHost(message.is_host || false);
        setHost(message.host || '');
      } else if (message.type === 'available_activities') {
        setActivities(message.activities || []);
      } else if (message.type === 'activity_state') {
        setActivityState(message as ActivityState);
        setCurrentActivity(message.activity_type || 'snake');
      } else if (message.type === 'activity_changed') {
        setCurrentActivity(message.activity_type ?? 'snake');
        addMessage({
          type: 'activity_changed',
          message: `Activity changed to ${message.activity_name} by ${message.changed_by}`,
          activity_type: message.activity_type,
          activity_name: message.activity_name,
          changed_by: message.changed_by
        } as Message);
      } else if (message.type === 'snake_state' ||
                 message.type === 'youtube_sync_update' ||
                 message.type === 'youtube_video_loaded' ||
                 message.type === 'youtube_play' ||
                 message.type === 'youtube_pause' ||
                 message.type === 'youtube_seek' ||
                 message.type === 'youtube_rate_changed' ||
                 message.type === 'youtube_master_changed' ||
                 message.type === 'snake_player_joined' ||
                 message.type === 'snake_game_started' ||
                 message.type === 'snake_game_restarted') {
        // Log YouTube messages for debugging with host/guest identification
        if (message.type.startsWith('youtube_')) {
          const userType = isHost ? 'HOST' : 'GUEST';
          const logMsg = `[${userType}] YouTube broadcast received`;
          DebugLogger.log(logMsg, message);
        }
        // Activity-specific state updates - update based on message type
        if (activityState && activityState.activity_type === 'youtube') {
          setActivityState(prev => {
            if (!prev || prev.activity_type !== 'youtube') return prev;

            // Handle YouTube-specific updates
            const update = message as YouTubeStateUpdate & { type: string };
            const currentState = prev.state as YouTubeState;
            
            if (message.type === 'youtube_video_loaded') {
              return {
                ...prev,
                state: {
                  ...currentState,
                  video_id: update.video_id ?? currentState.video_id,
                  current_time: update.current_time ?? currentState.current_time
                }
              } as YouTubeActivityState;
            } else if (message.type === 'youtube_sync_update') {
              return {
                ...prev,
                state: {
                  ...currentState,
                  video_id: update.video_id ?? currentState.video_id,
                  current_time: update.current_time ?? currentState.current_time,
                  is_playing: update.is_playing ?? currentState.is_playing,
                  playback_rate: update.playback_rate ?? currentState.playback_rate,
                  last_action_user: update.last_action_user ?? currentState.last_action_user
                }
              } as YouTubeActivityState;
            } else if (message.type.startsWith('youtube_')) {
              // Other YouTube updates - merge properties
              const newState: YouTubeState = { ...currentState };
              if (update.current_time !== undefined) newState.current_time = update.current_time;
              if (update.is_playing !== undefined) newState.is_playing = update.is_playing;
              if (update.playback_rate !== undefined) newState.playback_rate = update.playback_rate;
              if (update.last_action_user !== undefined) newState.last_action_user = update.last_action_user;
              if (update.video_id !== undefined) newState.video_id = update.video_id;

              return {
                ...prev,
                state: newState
              } as YouTubeActivityState;
            }
            
            return prev;
          });
        }
      } else if (message.type === 'message' || message.type === 'user_joined' || message.type === 'user_left' || message.type === 'error' || message.type === 'activity_changed') {
        // Regular messages, user events, errors
        addMessage(message as Message);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected from WebSocket');
      setConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWsRef(ws);
  };

  const disconnect = () => {
    if (wsRef) {
      wsRef.close();
      setWsRef(null);
    }
  };

  // Update sendActivityAction to include debug logging since it's not in the store
  const sendActivityActionWithLogging = (action: Record<string, unknown>) => {
    // Log YouTube actions being sent with host/guest identification
    if (typeof action.type === 'string' && action.type.includes('youtube')) {
      const userType = isHost ? 'HOST' : 'GUEST';
      const logMsg = `[${userType}] Sending YouTube action to backend`;
      DebugLogger.log(logMsg, action);
    }
    sendActivityAction(action);
  };

  useEffect(() => {
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reset YouTube player status when switching away from YouTube
  // IMPORTANT: This must be called before any early returns to maintain hook order
  useEffect(() => {
    if (currentActivity !== 'youtube') {
      setYoutubePlayerStatus(null);
    }
  }, [currentActivity]);

  if (!connected) {
    return (
      <div className="max-w-2xl mx-auto p-5">
        <h1 className="text-3xl font-bold text-center mb-6 text-theater-text">Join Room with Activities</h1>
        <div className="flex gap-3 mb-5">
          <input
            type="text"
            placeholder="Room name"
            value={room}
            onChange={(e) => setRoom(e.target.value)}
            className="flex-1 px-3 py-2 border border-theater-border bg-theater-surface text-theater-text rounded-md focus:outline-none focus:ring-2 focus:ring-twitch-purple placeholder-theater-text-muted"
          />
          <input
            type="text"
            placeholder="Your name"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="flex-1 px-3 py-2 border border-theater-border bg-theater-surface text-theater-text rounded-md focus:outline-none focus:ring-2 focus:ring-twitch-purple placeholder-theater-text-muted"
          />
          <button
            onClick={connect}
            disabled={!username || !room}
            className="px-5 py-2 bg-twitch-purple text-white border-none rounded-md cursor-pointer disabled:bg-gray-600 disabled:cursor-not-allowed hover:bg-twitch-purple-dark transition-colors"
          >
            Connect
          </button>
        </div>
      </div>
    );
  }

  const renderActivity = () => {
    switch (currentActivity) {
      case 'snake':
        if (activityState && activityState.activity_type === 'snake') {
          return (
            <SnakeActivity
              state={activityState.state}
              config={(activityState as SnakeActivityState & { config?: { grid_width: number; grid_height: number; tick_rate: number; max_players: number } }).config ?? {
                grid_width: 30,
                grid_height: 30,
                tick_rate: 200,
                max_players: 4
              }}
              isPlayer={(activityState as SnakeActivityState & { is_player?: boolean }).is_player ?? false}
              onAction={sendActivityActionWithLogging}
            />
          );
        }
        break;
      case 'youtube':
        if (activityState && activityState.activity_type === 'youtube') {
          return (
            <YouTubeActivity
              state={activityState.state}
              onAction={sendActivityActionWithLogging}
              isHost={isHost}
              onPlayerStatusChange={setYoutubePlayerStatus}
            />
          );
        }
        break;
    }
    return <div>Loading activity...</div>;
  };

  // Theater mode for YouTube activity
  const isTheaterMode = currentActivity === 'youtube' && 
    activityState?.activity_type === 'youtube' && 
    (activityState.state as YouTubeState)?.video_id != null;

  return (
    <div className="min-h-screen transition-all duration-500 ease-out bg-gradient-to-br from-theater-bg to-theater-bg-light text-theater-text p-0 m-0">
      {!isTheaterMode && (
        <div className="p-5 bg-theater-surface border-b border-theater-border">
          <div className="max-w-6xl mx-auto flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-theater-text mb-2">Room: {room}</h1>
              <div className="text-theater-text-muted mb-2">
                Connected as: <strong className="text-theater-text">{username}</strong>
                {isHost && <span className="text-twitch-purple font-bold ml-2">(Host)</span>}
              </div>
              <div className="text-sm text-theater-text-muted">
                Host: {host} | Users: {activityState?.users?.length || 0}
              </div>
            </div>
            <div className="flex items-center">
              <ActivitySwitcher
                activities={activities}
                currentActivity={currentActivity}
                isHost={isHost}
                onActivityChange={changeActivity}
                isTheaterMode={false}
              />
            </div>
          </div>
        </div>
      )}

      {isTheaterMode && (
        <div className="sticky top-0 z-50 bg-black/90 backdrop-blur-md border-b border-theater-border px-5 py-2 animate-fade-in-slide">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <span className="text-lg font-semibold text-theater-text">{room}</span>
              <span className="text-sm text-theater-text-muted bg-white/10 px-2 py-1 rounded-full">
                {activityState?.users?.length || 0} viewers
              </span>
              {youtubePlayerStatus && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-theater-text">
                    API: {youtubePlayerStatus.isAPIReady ? '✅' : '⏳'}
                  </span>
                  <span className="text-theater-text">
                    Player: {youtubePlayerStatus.isPlayerReady ? '✅' : '⏳'}
                  </span>
                  {activityState?.activity_type === 'youtube' && (
                    <>
                      <span className="text-theater-text-muted">
                        Time: {Math.floor((activityState.state as YouTubeState).current_time || 0)}s
                      </span>
                      <span className="text-theater-text-muted">
                        Rate: {(activityState.state as YouTubeState).playback_rate || 1}x
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center gap-3">
              <ActivitySwitcher
                activities={activities}
                currentActivity={currentActivity}
                isHost={isHost}
                onActivityChange={changeActivity}
                isTheaterMode={true}
              />
              <span className="text-theater-text font-medium">{username}</span>
              {isHost && (
                <span className="bg-twitch-purple text-white px-2 py-1 rounded-full text-xs font-semibold uppercase">
                  Host
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      <div className={`${
        isTheaterMode
          ? 'flex h-[calc(100vh-100px)]'
          : 'flex gap-5 my-5 mx-auto max-w-6xl px-5'
      }`}>
        <div className={`${
          isTheaterMode
            ? 'flex-1 bg-theater-bg h-full'
            : 'flex-[2] min-h-[500px] bg-theater-surface border border-theater-border rounded-lg my-5'
        }`}>
          {renderActivity()}
        </div>

        <PersistentChat
          messages={messages}
          onSendMessage={sendMessage}
          isTheaterMode={isTheaterMode}
        />
      </div>
    </div>
  );
}

export default App;