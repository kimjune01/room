import { useState } from 'react';

interface YouTubeControlsProps {
  videoUrl: string;
  setVideoUrl: (value: string) => void;
  loadVideo: () => void;
  canLoadSeekRate: boolean;
}

export function YouTubeControls({
  videoUrl,
  setVideoUrl,
  loadVideo,
  canLoadSeekRate,
}: YouTubeControlsProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className={`absolute bottom-5 right-5 z-[100] bg-black/90 backdrop-blur-md rounded-lg ${
      isCollapsed ? 'p-2' : 'p-4'
    } ${
      !isCollapsed ? 'max-w-md w-full' : ''
    }`}>
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className={`text-white hover:bg-white/10 rounded text-xl leading-none focus:outline-none flex items-center justify-center ${
          isCollapsed ? 'p-0' : 'absolute top-2 right-2 p-1'
        }`}
        aria-label={isCollapsed ? 'Expand controls' : 'Collapse controls'}
      >
        {isCollapsed ? (
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            viewBox="0 0 24 24" 
            fill="currentColor" 
            className="w-12 h-12"
          >
            <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
          </svg>
        ) : (
          '▼'
        )}
      </button>

      {!isCollapsed && (
        <>
          <div className="bg-white/5 border border-white/10 mb-5 p-4 rounded-lg">
            <h4 className="text-white m-0 mb-3 font-medium">
              Load Video
            </h4>
            <div className="flex gap-3 items-center flex-wrap">
              <input
                type="text"
                placeholder="YouTube URL or Video ID"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                disabled={!canLoadSeekRate}
                className="bg-white/10 border border-white/20 text-white placeholder-white/50 focus:border-twitch-purple focus:ring-twitch-purple flex-1 min-w-[200px] px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={loadVideo}
                disabled={!canLoadSeekRate || !videoUrl}
                className={`${
                  !canLoadSeekRate || !videoUrl
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-twitch-purple hover:bg-twitch-purple-dark focus:ring-twitch-purple'
                } px-4 py-2 text-white border-none rounded-md cursor-pointer text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-opacity-50`}
              >
                Load
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
