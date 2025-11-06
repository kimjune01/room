import { create } from 'zustand';
import type { Message, Activity } from '../types';

interface AppState {
  // Connection state
  room: string;
  username: string;
  connected: boolean;
  host: string;
  isHost: boolean;

  // UI state
  messages: Message[];
  activities: Activity[];
  currentActivity: string;

  // WebSocket reference
  wsRef: WebSocket | null;

  // Actions
  setRoom: (room: string) => void;
  setUsername: (username: string) => void;
  setConnected: (connected: boolean) => void;
  setHost: (host: string) => void;
  setIsHost: (isHost: boolean) => void;
  setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
  setActivities: (activities: Activity[]) => void;
  setCurrentActivity: (activity: string) => void;
  setWsRef: (ws: WebSocket | null) => void;

  // Computed actions
  addMessage: (message: Message) => void;
  clearMessages: () => void;

  // Connection actions
  sendMessage: (message: string) => void;
  changeActivity: (activityType: string) => void;
  sendActivityAction: (action: any) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  room: 'testroom',
  username: '',
  connected: false,
  host: '',
  isHost: false,
  messages: [],
  activities: [],
  currentActivity: 'youtube',
  wsRef: null,

  // Basic setters
  setRoom: (room) => set({ room }),
  setUsername: (username) => set({ username }),
  setConnected: (connected) => set({ connected }),
  setHost: (host) => set({ host }),
  setIsHost: (isHost) => set({ isHost }),
  setMessages: (messages) => set((state) => ({
    messages: typeof messages === 'function' ? messages(state.messages) : messages
  })),
  setActivities: (activities) => set({ activities }),
  setCurrentActivity: (currentActivity) => set({ currentActivity }),
  setWsRef: (wsRef) => set({ wsRef }),

  // Computed actions
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  clearMessages: () => set({ messages: [] }),

  // Connection actions
  sendMessage: (message) => {
    const { wsRef } = get();
    if (wsRef) {
      wsRef.send(JSON.stringify({ type: 'message', message }));
    }
  },

  changeActivity: (activityType) => {
    const { wsRef, isHost } = get();
    if (wsRef && isHost) {
      wsRef.send(JSON.stringify({
        type: 'change_activity',
        activity_type: activityType
      }));
    }
  },

  sendActivityAction: (action) => {
    const { wsRef } = get();
    if (wsRef) {
      wsRef.send(JSON.stringify(action));
    }
  },
}));