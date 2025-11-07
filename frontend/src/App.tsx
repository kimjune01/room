import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
// Using Tailwind CSS classes instead of external CSS
import type { Message, ActivityState, WebSocketMessage, YouTubeStateUpdate, YouTubeState, YouTubeActivityState, Activity } from './types';
import { ActivitySwitcher } from './components/ActivitySwitcher';
import { PersistentChat } from './components/PersistentChat';
import { YouTubeActivity } from './components/YouTubeActivity';
import { DebugLogger } from './utils/debug-logger';

function App() {
  // Connection state
  const [room, setRoom] = useState('testroom');
  const [username, setUsername] = useState('');
  const [connected, setConnected] = useState(false);
  const [host, setHost] = useState('');
  const [isHost, setIsHost] = useState(false);

  // UI state
  const [messages, setMessages] = useState<Message[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [currentActivity, setCurrentActivity] = useState('youtube');

  // WebSocket reference
  const wsRef = useRef<WebSocket | null>(null);

  // Activity-specific state
  const [activityState, setActivityState] = useState<ActivityState | null>(null);
  const [youtubePlayerStatus, setYoutubePlayerStatus] = useState<{isAPIReady: boolean, isPlayerReady: boolean} | null>(null);

  // Helper functions
  const addMessage = useCallback((message: Message) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'message', message }));
    }
  }, []);

  const changeActivity = useCallback((activityType: string) => {
    if (wsRef.current && isHost) {
      wsRef.current.send(JSON.stringify({
        type: 'change_activity',
        activity_type: activityType
      }));
    }
  }, [isHost]);

  const sendActivityAction = useCallback((action: any) => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify(action));
    }
  }, []);


  const connect = () => {
    if (!username || !room) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/${room}/${username}`);

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as WebSocketMessage;

      if (message.type === 'role_assigned') {
        setIsHost(message.is_host || false);
        setHost(message.host || '');
      } else if (message.type === 'available_activities') {
        setActivities(message.activities || []);
      } else if (message.type === 'activity_state') {
        setActivityState(message as ActivityState);
        setCurrentActivity(message.activity_type || 'youtube');
      } else if (message.type === 'activity_changed') {
        setCurrentActivity(message.activity_type ?? 'youtube');
        addMessage({
          type: 'activity_changed',
          message: `Activity changed to ${message.activity_name} by ${message.changed_by}`,
          activity_type: message.activity_type,
          activity_name: message.activity_name,
          changed_by: message.changed_by
        } as Message);
      } else if (message.type === 'youtube_sync_update' ||
                 message.type === 'youtube_video_loaded' ||
                 message.type === 'youtube_play' ||
                 message.type === 'youtube_pause' ||
                 message.type === 'youtube_seek' ||
                 message.type === 'youtube_rate_changed' ||
                 message.type === 'youtube_master_changed') {
        // Optional: minimal logging for YouTube messages
        if (message.type.startsWith('youtube_')) {
          const userType = isHost ? 'HOST' : 'GUEST';
          DebugLogger.log(`[${userType}] YouTube: ${message.type}`, message);
        }
        // Activity-specific state updates - update based on message type
        // Simple check: process YouTube messages when we have YouTube activity state
        if (activityState && activityState.activity_type === 'youtube') {
            setActivityState(prev => {
            if (!prev || prev.activity_type !== 'youtube') return prev;

            // Handle YouTube-specific updates
            const update = message as YouTubeStateUpdate & { type: string };
            const currentState = prev.state as YouTubeState;

            if (message.type === 'youtube_video_loaded') {
              const newState = {
                ...currentState,
                video_id: update.video_id ?? currentState.video_id,
                current_time: update.current_time ?? currentState.current_time
              };

              // Only update if state actually changed
              if (newState.video_id === currentState.video_id &&
                  newState.current_time === currentState.current_time) {
                return prev;
              }

              return {
                ...prev,
                state: newState
              } as YouTubeActivityState;
            } else if (message.type === 'youtube_sync_update') {
              // Simple approach: apply server state immediately
              const newState = {
                ...currentState,
                video_id: update.video_id ?? currentState.video_id,
                current_time: update.current_time ?? currentState.current_time,
                is_playing: update.is_playing ?? currentState.is_playing,
                playback_rate: update.playback_rate ?? currentState.playback_rate,
                last_action_user: update.last_action_user ?? currentState.last_action_user
              };

              return {
                ...prev,
                state: newState
              } as YouTubeActivityState;
            } else if (message.type.startsWith('youtube_')) {
              // Simple approach: apply all YouTube updates immediately
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
      setConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  // Create stable wrapper function that doesn't recreate on every render
  const sendActivityActionWithLogging = useCallback((action: Record<string, unknown>) => {
    // Only log important actions to reduce noise
    if (typeof action.type === 'string' && action.type.includes('youtube')) {
      // Only log user-initiated actions, not sync updates
      const isUserAction = action.type === 'activity:youtube:play' ||
                          action.type === 'activity:youtube:pause' ||
                          action.type === 'activity:youtube:seek' ||
                          action.type === 'activity:youtube:load_video';

      if (isUserAction) {
        const userType = isHost ? 'HOST' : 'GUEST';
        const logMsg = `[${userType}] User action: ${action.type}`;
        DebugLogger.log(logMsg, action);

        // Track local action timestamp
        setActivityState(prev => {
          if (!prev || prev.activity_type !== 'youtube') return prev;
          return {
            ...prev,
            state: {
              ...prev.state,
              last_action_time: Date.now() / 1000
            }
          } as YouTubeActivityState;
        });
      }
    }

    sendActivityAction(action);
  }, [isHost, sendActivityAction]);

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

  // ALL HOOKS MUST BE CALLED BEFORE ANY CONDITIONAL RETURNS
  // Memoized expensive computations to prevent unnecessary re-renders
  const isTheaterMode = useMemo(() => {
    return currentActivity === 'youtube' &&
      activityState?.activity_type === 'youtube' &&
      (activityState.state as YouTubeState)?.video_id != null;
  }, [currentActivity, activityState]);

  // Memoized activity switcher props to prevent unnecessary re-renders
  const activitySwitcherProps = useMemo(() => ({
    activities,
    currentActivity,
    isHost,
    onActivityChange: changeActivity
  }), [activities, currentActivity, isHost, changeActivity]);

  // Memoized chat props to prevent unnecessary re-renders
  const chatProps = useMemo(() => ({
    messages,
    onSendMessage: sendMessage,
    isTheaterMode
  }), [messages, sendMessage, isTheaterMode]);

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
                {...activitySwitcherProps}
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
                {...activitySwitcherProps}
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
          {...chatProps}
        />
      </div>
    </div>
  );
}

export default App;