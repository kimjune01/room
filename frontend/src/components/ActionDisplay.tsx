interface ActionDisplayProps {
  lastAction: {
    user: string;
    type: string;
    timestamp: number;
  } | null;
  isTheaterMode?: boolean;
}

export function ActionDisplay({ lastAction, isTheaterMode }: ActionDisplayProps) {
  if (!lastAction) {
    return null;
  }

  const getActionIcon = (type: string): string => {
    switch (type) {
      case 'load_video':
        return '🎥';
      case 'play':
        return '▶️';
      case 'pause':
        return '⏸️';
      case 'seek':
        return '⏭️';
      case 'sync_request':
        return '🔄';
      case 'request_master':
        return '👑';
      default:
        return '📺';
    }
  };

  const getActionText = (type: string): string => {
    switch (type) {
      case 'load_video':
        return 'loaded a video';
      case 'play':
        return 'started playback';
      case 'pause':
        return 'paused playback';
      case 'seek':
        return 'seeked to new position';
      case 'sync_request':
        return 'requested sync';
      case 'request_master':
        return 'requested master control';
      default:
        return 'performed an action';
    }
  };

  return (
    <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10">
      <div className={`opacity-50 ${
        isTheaterMode
          ? 'bg-black/60 backdrop-blur-md border border-white/20 text-theater-text'
          : 'bg-gray-50 border border-gray-200 text-gray-700'
      } rounded-lg px-4 py-3 flex items-center gap-2 shadow-sm max-w-[300px]`}>
        <span className="text-lg min-w-[18px]">{getActionIcon(lastAction.type)}</span>
        <span className="text-sm whitespace-nowrap overflow-hidden text-ellipsis">
          <strong>{lastAction.user}</strong> {getActionText(lastAction.type)}
        </span>
      </div>
    </div>
  );
}