import { useCallback, useRef } from 'react';
import { useAppStore } from './useAppStore';
import type { Message, Activity } from '../types';

// Stable selectors to prevent infinite loops
const connectionSelector = (state: any) => ({
  room: state.room,
  username: state.username,
  connected: state.connected,
});

const userRoleSelector = (state: any) => ({
  isHost: state.isHost,
  host: state.host,
});

const activitySelector = (state: any) => ({
  activities: state.activities,
  currentActivity: state.currentActivity,
});

const chatSelector = (state: any) => ({
  messages: state.messages,
});

const activityActionsSelector = (state: any) => ({
  addMessage: state.addMessage,
  setIsHost: state.setIsHost,
  setHost: state.setHost,
  setActivities: state.setActivities,
  setCurrentActivity: state.setCurrentActivity,
});

const connectionActionsSelector = (state: any) => ({
  setRoom: state.setRoom,
  setUsername: state.setUsername,
  setConnected: state.setConnected,
  setWsRef: state.setWsRef,
});

// Selective subscriptions to prevent over-rendering

// Connection-related state (for login screen)
export const useConnectionState = () => useAppStore(connectionSelector);

// User role state (for UI permissions)
export const useUserRoleState = () => useAppStore(userRoleSelector);

// Activity state (for activity management)
export const useActivityState = () => useAppStore(activitySelector);

// Chat state (for chat component)
export const useChatState = () => useAppStore(chatSelector);

// WebSocket reference (for connection management)
export const useWebSocketRef = () => useAppStore((state) => state.wsRef);

// Optimized hook for WebSocket operations - only re-renders when wsRef changes
export const useWebSocketActions = () => {
  const wsRef = useWebSocketRef();

  const sendMessage = useCallback((message: string) => {
    if (wsRef) {
      wsRef.send(JSON.stringify({ type: 'message', message }));
    }
  }, [wsRef]);

  const changeActivity = useCallback((activityType: string) => {
    const isHost = useAppStore.getState().isHost;
    if (wsRef && isHost) {
      wsRef.send(JSON.stringify({
        type: 'change_activity',
        activity_type: activityType
      }));
    }
  }, [wsRef]);

  const sendActivityAction = useCallback((action: any) => {
    if (wsRef) {
      wsRef.send(JSON.stringify(action));
    }
  }, [wsRef]);

  return { sendMessage, changeActivity, sendActivityAction };
};

// Optimized hook for activity-specific operations
export const useActivityActions = () => useAppStore(activityActionsSelector);

// Optimized hook for connection management
export const useConnectionActions = () => useAppStore(connectionActionsSelector);