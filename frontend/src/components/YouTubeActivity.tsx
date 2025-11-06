import { useState } from 'react';
import type { YouTubeState } from '../types';
import { YouTubePlayer } from './YouTubePlayer';
import { ActionDisplay } from './ActionDisplay';
import { YouTubeControls } from './YouTubeControls';

interface YouTubeActivityProps {
  state: YouTubeState;
  onAction: (action: Record<string, unknown>) => void;
  isHost?: boolean;
  onPlayerStatusChange?: (status: {isAPIReady: boolean, isPlayerReady: boolean}) => void;
}

export function YouTubeActivity({ state, onAction, isHost = false, onPlayerStatusChange }: YouTubeActivityProps) {
  const [videoUrl, setVideoUrl] = useState('');
  const [seekTime, setSeekTime] = useState('');

  const extractVideoId = (url: string): string | null => {
    const trimmedUrl = url.trim();
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/,
      /youtube\.com\/embed\/([^&\n?#]+)/,
      /^([a-zA-Z0-9_-]{11})$/  // Direct video ID
    ];

    for (const pattern of patterns) {
      const match = trimmedUrl.match(pattern);
      if (match) return match[1].trim();
    }
    return null;
  };

  const loadVideo = () => {
    const videoId = extractVideoId(videoUrl);
    if (!videoId) {
      alert('Please enter a valid YouTube URL or video ID');
      return;
    }

    onAction({
      type: 'activity:youtube:load_video',
      video_id: videoId,
      start_time: parseFloat(seekTime) || 0
    });
    setVideoUrl('');
    setSeekTime('');
  };

  // Universal access - anyone can do any action (throttled by backend)
  const canPlayPause = true;
  const canLoadSeekRate = true; // Force refresh

  // Theater mode detection
  const isTheaterMode = !!state.video_id;
  const hasVideo = !!state.video_id;

  return (
    <div className={`relative ${
      isTheaterMode
        ? 'h-full flex flex-col bg-theater-bg min-h-0'
        : 'text-left p-5'
    }`}>

      {hasVideo ? (
        <>
          <ActionDisplay lastAction={state.last_action || null} isTheaterMode={isTheaterMode} />
          <YouTubePlayer
            videoId={state.video_id!}
            currentTime={state.current_time || 0}
            isPlaying={state.is_playing || false}
            playbackRate={state.playback_rate || 1}
            isAuthoritative={false}
            isHost={isHost}
            isTheaterMode={isTheaterMode}
            onTimeUpdate={() => {
              // Don't send time updates - backend is authoritative
            }}
            onPlay={() => {
              // User clicked play on native controls - send to backend
              if (canPlayPause) {
                onAction({ type: 'activity:youtube:play' });
              }
            }}
            onPause={() => {
              // User clicked pause on native controls - send to backend
              if (canPlayPause) {
                onAction({ type: 'activity:youtube:pause' });
              }
            }}
            onSeek={(time) => {
              // User seeked using native controls - send to backend
              if (canLoadSeekRate) {
                onAction({
                  type: 'activity:youtube:seek',
                  time
                });
              }
            }}
            onBuffering={(isBuffering) => {
              // Send buffering status to server
              if (isBuffering) {
                onAction({ type: 'activity:youtube:buffer_start' });
              } else {
                onAction({ type: 'activity:youtube:buffer_end' });
              }
            }}
            onStateReport={(state) => {
              // Report current playback state to server when authoritative
              onAction({
                type: 'activity:youtube:state_report',
                current_time: state.current_time,
                is_playing: state.is_playing,
                playback_rate: state.playback_rate,
                client_timestamp: Date.now() / 1000 // Convert to seconds to match backend
              });
            }}
            onStatusChange={onPlayerStatusChange}
          />
          <YouTubeControls
            videoUrl={videoUrl}
            setVideoUrl={setVideoUrl}
            loadVideo={loadVideo}
            canLoadSeekRate={canLoadSeekRate}
          />
        </>
      ) : (
        <div className={`${
          isTheaterMode
            ? 'h-full flex items-center justify-center bg-theater-bg'
            : 'min-h-[500px] flex items-center justify-center bg-theater-surface border border-theater-border rounded-lg'
        }`}>
          <div className={`${
            isTheaterMode
              ? 'w-full max-w-2xl px-8'
              : 'w-full max-w-xl px-5'
          }`}>
            <div className="text-center mb-8">
              <div className={`${
                isTheaterMode
                  ? 'text-6xl mb-4 text-theater-text-muted'
                  : 'text-5xl mb-4 text-theater-text-muted'
              }`}>
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  viewBox="0 0 24 24" 
                  fill="currentColor" 
                  className="mx-auto"
                  style={{ width: isTheaterMode ? '80px' : '64px', height: isTheaterMode ? '80px' : '64px' }}
                >
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>
              </div>
              <h2 className={`${
                isTheaterMode
                  ? 'text-2xl font-bold text-theater-text mb-2'
                  : 'text-xl font-bold text-theater-text mb-2'
              }`}>
                Load a YouTube Video
              </h2>
              <p className={`${
                isTheaterMode
                  ? 'text-theater-text-muted text-base'
                  : 'text-theater-text-muted text-sm'
              }`}>
                Enter a YouTube URL or video ID to get started
              </p>
            </div>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="YouTube URL or Video ID"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && videoUrl && canLoadSeekRate) {
                    loadVideo();
                  }
                }}
                disabled={!canLoadSeekRate}
                className={`${
                  isTheaterMode
                    ? 'w-full px-4 py-3 text-base'
                    : 'w-full px-4 py-2.5 text-sm'
                } bg-theater-surface border border-theater-border text-theater-text placeholder-theater-text-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-twitch-purple focus:border-twitch-purple disabled:opacity-50 disabled:cursor-not-allowed`}
              />
              <button
                onClick={loadVideo}
                disabled={!canLoadSeekRate || !videoUrl}
                className={`${
                  isTheaterMode
                    ? 'w-full px-6 py-4 text-lg font-semibold'
                    : 'w-full px-6 py-3 text-base font-semibold'
                } ${
                  !canLoadSeekRate || !videoUrl
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-twitch-purple hover:bg-twitch-purple-dark text-white'
                } rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-twitch-purple focus:ring-opacity-50`}
              >
                Load Video
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}