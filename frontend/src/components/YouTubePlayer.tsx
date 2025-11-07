import { useEffect, useRef, useState } from 'react';
import { DebugLogger } from '../utils/debug-logger';
import type { YouTubePlayer as YouTubePlayerType, YouTubePlayerEvent } from '../types';


// Constants for better maintainability - reduced for immediate response
const SYNC_THRESHOLD_SECONDS = 1; // Reduced from 2 to 1 second
const INITIAL_SYNC_DELAY_MS = 500; // Reduced from 1000 to 500ms
const SYNC_INTERVAL_MS = 500; // Reduced from 1000 to 500ms for faster sync

interface YouTubePlayerProps {
  videoId: string;
  currentTime: number;
  isPlaying: boolean;
  playbackRate: number;
  isAuthoritative: boolean;
  isHost?: boolean;
  isTheaterMode?: boolean;
  onTimeUpdate?: (time: number) => void;
  onPlay?: () => void;
  onPause?: () => void;
  onSeek?: (time: number) => void;
  onBuffering?: (isBuffering: boolean) => void;
  onStateReport?: (state: {current_time: number, is_playing: boolean, playback_rate: number}) => void;
  onStatusChange?: (status: {isAPIReady: boolean, isPlayerReady: boolean}) => void;
}

function YouTubePlayerComponent({
  videoId,
  currentTime,
  isPlaying,
  playbackRate,
  isAuthoritative,
  isHost = false,
  isTheaterMode = false,
  onTimeUpdate,
  onPlay,
  onPause,
  onSeek,
  onBuffering,
  onStateReport,
  onStatusChange
}: YouTubePlayerProps) {
  const playerRef = useRef<YouTubePlayerType | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAPIReady, setIsAPIReady] = useState(false);
  const [isPlayerReady, setIsPlayerReady] = useState(false);
  const isInitialSyncRef = useRef(true);
  const lastSyncTime = useRef<number>(0);
  const lastKnownTime = useRef<number>(0);
  const lastKnownState = useRef<number>(-1);
  const isProgrammaticChange = useRef(false);
  const syncTimerRef = useRef<number | null>(null);

  // Helper for consistent logging
  const log = (message: string, data?: unknown): void => {
    const userType = isHost ? 'HOST' : 'GUEST';
    const logMsg = `[${userType}] YouTubePlayer: ${message}`;
    DebugLogger.log(logMsg, data);
  };

  // Helper to get player state name
  const getPlayerStateName = (state: number): string => {
    if (!window.YT) return `State ${state}`;
    const states: Record<number, string> = {
      [-1]: 'UNSTARTED',
      [window.YT.PlayerState.ENDED]: 'ENDED',
      [window.YT.PlayerState.PLAYING]: 'PLAYING',
      [window.YT.PlayerState.PAUSED]: 'PAUSED',
      [window.YT.PlayerState.BUFFERING]: 'BUFFERING',
      [window.YT.PlayerState.CUED]: 'CUED'
    };
    return states[state] || `UNKNOWN(${state})`;
  };

  // Log component mount/unmount and cleanup timers
  useEffect(() => {
    log('Component mounted', { videoId, isAuthoritative });
    return () => {
      log('Component unmounting');
      // Clean up sync timer
      if (syncTimerRef.current !== null) {
        clearTimeout(syncTimerRef.current);
        syncTimerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load YouTube IFrame API
  useEffect(() => {
    if (window.YT && window.YT.Player) {
      setIsAPIReady(true);
      return;
    }

    // Load the IFrame Player API code asynchronously
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

    // API will call this function when ready
    window.onYouTubeIframeAPIReady = () => {
      setIsAPIReady(true);
    };
  }, []);

  // Report status changes to parent
  useEffect(() => {
    onStatusChange?.({ isAPIReady, isPlayerReady });
  }, [isAPIReady, isPlayerReady, onStatusChange]);

  // Initialize player when API is ready
  useEffect(() => {
    if (!isAPIReady || !containerRef.current || !videoId) return;

    log('Player initialization effect running', { videoId });

    // Destroy existing player
    if (playerRef.current) {
      log('Destroying existing player');
      playerRef.current.destroy();
    }

    // Create new player - adaptive sizing for theater mode
    // YouTube API accepts HTMLElement or string, but our types say string
    // We'll use the element directly by casting (the API actually supports this)
    const containerElement = containerRef.current;
    if (!containerElement.id) {
      containerElement.id = `youtube-player-${Date.now()}`;
    }
    playerRef.current = new window.YT.Player(containerElement.id, {
      height: '100%',
      width: '100%',
      videoId: videoId,
      playerVars: {
        enablejsapi: 1,
        controls: 1, // Show native controls for user interaction
        disablekb: 0, // Enable keyboard controls
        fs: 1, // Show fullscreen button
        rel: 0, // Don't show related videos
        modestbranding: 1, // Modest YouTube branding
        playsinline: 1, // Play inline on mobile
        start: Math.floor(currentTime)
      },
      events: {
        onReady: (event: YouTubePlayerEvent) => {
          log('YouTube player ready');
          setIsPlayerReady(true);

          // Set playback rate
          event.target.setPlaybackRate(playbackRate);

          // Sync to current room state
          if (currentTime > 0) {
            event.target.seekTo(currentTime, true);
          }

          // Ensure player respects the current playing state
          // Don't auto-play, sync to room state
          if (!isPlaying) {
            event.target.pauseVideo();
          }

          log('Player synced to room state', { currentTime, isPlaying, playbackRate });

          // Complete initial sync after a short delay
          log('Starting initial sync timer...');
          syncTimerRef.current = window.setTimeout(() => {
            log('Initial sync timer fired, setting isInitialSync to false');
            isInitialSyncRef.current = false;
            try {
              lastKnownTime.current = event.target.getCurrentTime();
              lastKnownState.current = event.target.getPlayerState();
            } catch (error) {
              log('Error in initial sync completion', { error: error instanceof Error ? error.message : 'Unknown error' });
            }
            log('Initial sync completed - player events now active');
          }, INITIAL_SYNC_DELAY_MS);
        },
        onStateChange: (event: YouTubePlayerEvent) => {
          const playerState = event.data;
          const player = event.target;
          log('Player state changed', { playerState, playerStateName: getPlayerStateName(playerState) });

          // Don't trigger callbacks during initial sync to prevent new users
          // from affecting the room's playback state
          if (isInitialSyncRef.current) {
            log('Ignoring state change during initial sync', { playerState });
            lastKnownState.current = playerState;
            try {
              lastKnownTime.current = player.getCurrentTime();
            } catch (error) {
              log('Error getting current time during initial sync', { error: error instanceof Error ? error.message : 'Unknown error' });
            }
            return;
          }

          // Detect user interactions and send to backend
          // Skip if this is a programmatic change from sync
          if (isProgrammaticChange.current) {
            log('Ignoring programmatic state change', { playerState });
            lastKnownTime.current = player.getCurrentTime();
            lastKnownState.current = playerState;
            return;
          }

          try {
            const currentTime = player.getCurrentTime();

            // Detect seek: time changed significantly without state change
            if (lastKnownState.current === playerState &&
                Math.abs(currentTime - lastKnownTime.current) > 2) {
              log('Detected seek', { from: lastKnownTime.current, to: currentTime });
              onSeek?.(currentTime);
            }

            // Detect play/pause state changes
            if (lastKnownState.current !== playerState) {
              if (playerState === window.YT.PlayerState.PLAYING &&
                  lastKnownState.current !== window.YT.PlayerState.PLAYING) {
                log('User clicked play');
                onPlay?.();
              } else if (playerState === window.YT.PlayerState.PAUSED &&
                         lastKnownState.current !== window.YT.PlayerState.PAUSED) {
                log('User clicked pause');
                onPause?.();
              }
            }
            
            lastKnownTime.current = currentTime;
            lastKnownState.current = playerState;
          } catch (error) {
            console.error('Error in onStateChange:', error);
          }

          // Send buffering status
          switch (playerState) {
            case window.YT.PlayerState.PLAYING:
              onBuffering?.(false);
              break;
            case window.YT.PlayerState.PAUSED:
              onBuffering?.(false);
              break;
            case window.YT.PlayerState.BUFFERING:
              onBuffering?.(true);
              break;
            case window.YT.PlayerState.ENDED:
              onBuffering?.(false);
              break;
          }
        },
        onError: (event: { data: number }) => {
          console.error('YouTube player error:', event.data);
        }
      }
    });

    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
    // Only recreate player when API loads or video changes - NOT on play/pause state changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAPIReady, videoId]);

  // Reset initial sync flag when video changes
  useEffect(() => {
    isInitialSyncRef.current = true;
  }, [videoId]);

  // Sync player state with backend (only for non-authoritative clients)
  useEffect(() => {
    if (!isPlayerReady || !playerRef.current || isAuthoritative) {
      return;
    }

    const player = playerRef.current;
    const now = Date.now();

    try {
      // Additional validation: ensure player methods exist
      if (typeof player.getPlayerState !== 'function' ||
          typeof player.playVideo !== 'function' ||
          typeof player.pauseVideo !== 'function') {
        log('Player methods not available yet, skipping sync');
        return;
      }

      // Sync playback state (only when NOT authoritative)
      const playerState = player.getPlayerState();
      const shouldBePlaying = isPlaying;
      const isCurrentlyPlaying = playerState === window.YT.PlayerState.PLAYING;

      if (shouldBePlaying && !isCurrentlyPlaying) {
        isProgrammaticChange.current = true;
        player.playVideo();
        setTimeout(() => { isProgrammaticChange.current = false; }, 100);
      } else if (!shouldBePlaying && isCurrentlyPlaying) {
        isProgrammaticChange.current = true;
        player.pauseVideo();
        setTimeout(() => { isProgrammaticChange.current = false; }, 100);
      }

      // Sync time (avoid frequent seeking, only for non-authoritative clients)
      if (now - lastSyncTime.current > SYNC_INTERVAL_MS) {
        if (typeof player.getCurrentTime !== 'function' || typeof player.seekTo !== 'function') {
          log('Player time methods not available yet, skipping time sync');
          return;
        }

        const playerTime = player.getCurrentTime();
        const timeDiff = Math.abs(playerTime - currentTime);

        if (timeDiff > SYNC_THRESHOLD_SECONDS) {
          isProgrammaticChange.current = true;
          player.seekTo(currentTime, true);
          setTimeout(() => { isProgrammaticChange.current = false; }, 100);
        }

        lastSyncTime.current = now;
      }

      // Sync playback rate (only for non-authoritative clients)
      if (typeof player.getPlaybackRate !== 'function' || typeof player.setPlaybackRate !== 'function') {
        log('Player rate methods not available yet, skipping rate sync');
        return;
      }
      const currentRate = player.getPlaybackRate();
      if (Math.abs(currentRate - playbackRate) > 0.01) {
        player.setPlaybackRate(playbackRate);
      }

    } catch (error) {
      console.error('Error syncing player:', error);
    }
  }, [isPlayerReady, isPlaying, currentTime, playbackRate, isAuthoritative]);

  // Time update interval and seek detection
  useEffect(() => {
    if (!isPlayerReady || !playerRef.current || isInitialSyncRef.current) return;

    const interval = setInterval(() => {
      try {
        const player = playerRef.current;
        if (!player) return;
        const currentTime = player.getCurrentTime();
        const playerState = player.getPlayerState();
        const isCurrentlyPlaying = playerState === window.YT.PlayerState.PLAYING;
        
        // Detect seek: time changed significantly beyond expected playback
        const expectedTime = lastKnownTime.current + (isCurrentlyPlaying ? (SYNC_INTERVAL_MS / 1000) : 0);
        const timeDiff = Math.abs(currentTime - expectedTime);

        if (timeDiff > 2 && Math.abs(currentTime - lastKnownTime.current) > 2) {
          onSeek?.(currentTime);
          lastKnownTime.current = currentTime;
        } else {
          lastKnownTime.current = currentTime;
        }
        
        onTimeUpdate?.(currentTime);
      } catch (error) {
        console.error('Error getting current time:', error);
      }
    }, SYNC_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [isPlayerReady, onTimeUpdate, onSeek]);

  // State reporting interval for authoritative client
  useEffect(() => {
    if (!isPlayerReady || !playerRef.current || !isAuthoritative || !onStateReport) return;

    const interval = setInterval(() => {
      try {
        const player = playerRef.current;
        if (!player) return;
        const current_time = player.getCurrentTime();
        const playerState = player.getPlayerState();
        const is_playing = playerState === window.YT.PlayerState.PLAYING;
        const playback_rate = player.getPlaybackRate();

        onStateReport({
          current_time,
          is_playing,
          playback_rate
        });
      } catch (error) {
        console.error('Error reporting state:', error);
      }
    }, 2000); // Report every 2 seconds when authoritative

    return () => clearInterval(interval);
  }, [isPlayerReady, isAuthoritative, onStateReport]);

  if (!videoId) {
    return (
      <div className={`${
        isTheaterMode
          ? 'flex-1 flex items-center justify-center bg-black text-theater-text-muted'
          : 'py-15 px-5 bg-gray-50 border-2 border-dashed border-gray-200 rounded-lg text-gray-500 text-center'
      }`}>
        <p>No video loaded</p>
      </div>
    );
  }

  return (
    <div className={`${
      isTheaterMode
        ? 'flex-1 flex flex-col bg-black relative min-h-0'
        : 'my-5 text-center'
    }`}>
      <div
        ref={containerRef}
        className={`${
          isTheaterMode
            ? 'w-full flex-1 min-h-0'
            : 'max-w-full mx-auto'
        }`}
      />

      {/* Status indicators - only show in non-theater mode */}
      {!isTheaterMode && (
        <div className="flex justify-center gap-4 my-3 text-sm">
          <span className={isAPIReady
            ? 'bg-green-100 text-green-800 px-2 py-1 rounded font-bold'
            : 'bg-yellow-100 text-yellow-800 px-2 py-1 rounded font-bold'
          }>
            API: {isAPIReady ? '✅' : '⏳'}
          </span>
          <span className={isPlayerReady
            ? 'bg-green-100 text-green-800 px-2 py-1 rounded font-bold'
            : 'bg-yellow-100 text-yellow-800 px-2 py-1 rounded font-bold'
          }>
            Player: {isPlayerReady ? '✅' : '⏳'}
          </span>
          <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded font-mono">
            Time: {Math.floor(currentTime)}s
          </span>
          <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded font-mono">
            Rate: {playbackRate}x
          </span>
        </div>
      )}

    </div>
  );
}

// Export component without memo for immediate re-renders and sync
export const YouTubePlayer = YouTubePlayerComponent;