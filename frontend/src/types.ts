export interface Activity {
  type: string;
  name: string;
  description: string;
}

// Union type for all possible activity states
export type ActivityState = SnakeActivityState | YouTubeActivityState;

export interface SnakeActivityState {
  type: 'activity_state';
  activity_type: 'snake';
  activity_name: string;
  state: SnakeState;
  users: string[];
}

export interface YouTubeActivityState {
  type: 'activity_state';
  activity_type: 'youtube';
  activity_name: string;
  state: YouTubeState;
  users: string[];
}

export interface SnakePosition {
  x: number;
  y: number;
}

export interface SnakePlayer {
  positions: SnakePosition[];
  direction: string;
  alive: boolean;
  score: number;
}

export interface SnakeState {
  status: 'waiting' | 'playing' | 'finished';
  players: Record<string, SnakePlayer>;
  food: SnakePosition[];
  tick_count: number;
  winner: string | null;
}

export interface YouTubeState {
  video_id: string | null;
  current_time: number;
  is_playing: boolean;
  playback_rate: number;
  last_action_user: string | null;
  buffering_users: string[];
  is_buffering: boolean;
  last_action?: {
    user: string;
    type: string;
    timestamp: number;
  };
  last_action_time?: number; // Local timestamp when user initiated an action (client-side only)
}

// Action types for activities
export type SnakeAction =
  | { type: 'activity:snake:join_game' }
  | { type: 'activity:snake:start_game' }
  | { type: 'activity:snake:restart_game' }
  | { type: 'activity:snake:change_direction'; direction: string };

export type YouTubeAction =
  | { type: 'activity:youtube:load_video'; video_id: string }
  | { type: 'activity:youtube:play' }
  | { type: 'activity:youtube:pause' }
  | { type: 'activity:youtube:seek'; time: number }
  | { type: 'activity:youtube:set_rate'; rate: number }
  | { type: 'activity:youtube:buffering_start' }
  | { type: 'activity:youtube:buffering_end' }
  | { type: 'activity:youtube:sync'; current_time: number; is_playing: boolean; playback_rate: number };

export type ActivityAction = SnakeAction | YouTubeAction;

// Message types for WebSocket communication
export type Message =
  | ChatMessage
  | RoleAssignedMessage
  | ActivityChangedMessage
  | AvailableActivitiesMessage
  | UserJoinedMessage
  | UserLeftMessage
  | ErrorMessage
  | ActivityStateMessage;

export interface ChatMessage {
  type: 'message';
  username: string;
  message: string;
  own_message?: boolean;
}

export interface RoleAssignedMessage {
  type: 'role_assigned';
  role: 'host' | 'participant';
  is_host: boolean;
  host: string;
}

export interface ActivityChangedMessage {
  type: 'activity_changed';
  activity_type: string;
  activity_name: string;
  changed_by: string;
}

export interface AvailableActivitiesMessage {
  type: 'available_activities';
  activities: Activity[];
}

export interface UserJoinedMessage {
  type: 'user_joined';
  username: string;
  message: string;
}

export interface UserLeftMessage {
  type: 'user_left';
  username: string;
  message: string;
}

export interface ErrorMessage {
  type: 'error';
  message: string;
}

export interface ActivityStateMessage {
  type: 'activity_state';
  activity_type: string;
  activity_name: string;
  state: SnakeState | YouTubeState;
  users: string[];
}

// WebSocket message types (union of all possible incoming messages)
export type WebSocketMessage =
  | Message
  | RoleAssignedMessage
  | AvailableActivitiesMessage
  | ActivityStateMessage
  | {
      type: 'snake_state' | 'snake_player_joined' | 'snake_game_started' | 'snake_game_restarted';
      state?: SnakeState;
      [key: string]: unknown;
    }
  | {
      type: 'youtube_sync_update' | 'youtube_video_loaded' | 'youtube_play' | 'youtube_pause' | 'youtube_seek' | 'youtube_rate_changed' | 'youtube_master_changed';
      video_id?: string;
      current_time?: number;
      is_playing?: boolean;
      playback_rate?: number;
      last_action_user?: string;
      [key: string]: unknown;
    };

// Helper type for YouTube state updates
export interface YouTubeStateUpdate {
  video_id?: string;
  current_time?: number;
  is_playing?: boolean;
  playback_rate?: number;
  last_action_user?: string;
}

// YouTube IFrame API types
export interface YouTubePlayer {
  playVideo(): void;
  pauseVideo(): void;
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  getPlayerState(): number;
  getCurrentTime(): number;
  getPlaybackRate(): number;
  setPlaybackRate(suggestedRate: number): void;
  loadVideoById(videoId: string): void;
  destroy(): void;
}

export interface YouTubePlayerEvent {
  target: YouTubePlayer;
  data: number;
}

// Extend Window interface for YouTube API
declare global {
  interface Window {
    YT: {
      Player: new (
        elementId: string,
        config: {
          height?: string | number;
          width?: string | number;
          videoId?: string;
          events?: {
            onReady?: (event: YouTubePlayerEvent) => void;
            onStateChange?: (event: YouTubePlayerEvent) => void;
            onPlaybackRateChange?: (event: YouTubePlayerEvent) => void;
            onError?: (event: { data: number }) => void;
          };
          playerVars?: Record<string, unknown>;
        }
      ) => YouTubePlayer;
      PlayerState: {
        UNSTARTED: number;
        ENDED: number;
        PLAYING: number;
        PAUSED: number;
        BUFFERING: number;
        CUED: number;
      };
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}