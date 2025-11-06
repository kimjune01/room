import type { Activity } from '../types';

interface ActivitySwitcherProps {
  activities: Activity[];
  currentActivity: string;
  isHost: boolean;
  onActivityChange: (activityType: string) => void;
  isTheaterMode?: boolean;
}

export function ActivitySwitcher({ activities, currentActivity, isHost, onActivityChange, isTheaterMode }: ActivitySwitcherProps) {
  if (!isHost) {
    return (<></>);
  }

  return (
    <div className="flex items-center">
      <label
        htmlFor="activity-select"
        className={`${
          isTheaterMode ? 'text-theater-text' : 'text-theater-text-muted'
        } mr-2 text-sm`}
      >
        Activity:
      </label>
      <select
        id="activity-select"
        value={currentActivity}
        onChange={(e) => onActivityChange(e.target.value)}
        className={`${
          isTheaterMode
            ? 'bg-theater-bg border-theater-border text-theater-text focus:border-twitch-purple'
            : 'bg-theater-surface border-theater-border text-theater-text focus:border-twitch-purple'
        } px-3 py-1.5 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-opacity-50 ${
          isTheaterMode ? 'focus:ring-twitch-purple' : 'focus:ring-twitch-purple'
        }`}
      >
        {activities.map((activity) => (
          <option key={activity.type} value={activity.type}>
            {activity.name}
          </option>
        ))}
      </select>
    </div>
  );
}