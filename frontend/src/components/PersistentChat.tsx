import { useState } from 'react';
import type { Message } from '../types';

interface PersistentChatProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isTheaterMode?: boolean;
}

export function PersistentChat({ messages, onSendMessage, isTheaterMode }: PersistentChatProps) {
  const [inputMessage, setInputMessage] = useState('');

  const sendMessage = () => {
    if (inputMessage.trim()) {
      onSendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  const chatMessages = messages.filter((msg: any) =>
    msg.type === 'message' ||
    msg.type === 'user_joined' ||
    msg.type === 'user_left' ||
    msg.type === 'activity_changed' ||
    msg.type === 'youtube_chat_event'
  );

  return (
    <div className={`${
      isTheaterMode
        ? 'bg-theater-surface border border-theater-border h-full max-w-[340px] min-w-[320px]'
        : 'flex-1 max-w-[350px] min-w-[300px] bg-white border border-gray-200 h-[500px] rounded-lg'
    } flex flex-col`}>
      <div className={`${
        isTheaterMode
          ? 'bg-theater-surface-light border-theater-border'
          : 'bg-gray-50 border-gray-200 rounded-t-lg'
      } px-4 py-3 border-b`}>
        <h3 className={`${
          isTheaterMode ? 'text-theater-text' : 'text-gray-700'
        } text-lg font-medium m-0`}>
          💬 Chat
        </h3>
      </div>

      <div className={`${
        isTheaterMode ? 'bg-theater-surface' : 'bg-white'
      } flex-1 overflow-y-auto p-4`}>
        {chatMessages.map((msg: any, index) => (
          <div
            key={index}
            className={`my-2 px-3 py-2 rounded-lg text-sm ${
              msg.own_message
                ? isTheaterMode
                  ? 'bg-twitch-purple text-white text-right ml-auto border border-twitch-purple-dark max-w-[80%]'
                  : 'bg-blue-600 text-white text-right ml-auto border border-blue-700 max-w-[80%]'
                : msg.type === 'user_joined' || msg.type === 'user_left' || msg.type === 'activity_changed'
                ? isTheaterMode
                  ? 'bg-yellow-900/20 text-center text-yellow-300 border border-yellow-700 text-xs italic'
                  : 'bg-yellow-50 text-center text-yellow-800 border border-yellow-200 text-xs italic'
                : isTheaterMode
                ? 'bg-theater-surface-light text-theater-text border border-theater-border'
                : 'bg-gray-50 text-gray-800 border border-gray-200'
            }`}
          >
            {msg.type === 'message' ? (
              <>
                <strong>{msg.username}:</strong> {msg.message}
              </>
            ) : msg.type === 'youtube_chat_event' ? (
              <span className="youtube-event">{msg.message}</span>
            ) : (
              <em>{msg.message}</em>
            )}
          </div>
        ))}
      </div>

      <div className={`${
        isTheaterMode
          ? 'bg-theater-surface-light border-theater-border'
          : 'bg-gray-50 border-gray-200 rounded-b-lg'
      } px-4 py-3 border-t flex gap-3`}>
        <input
          type="text"
          placeholder="Type a message..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          className={`${
            isTheaterMode
              ? 'bg-theater-bg border-theater-border text-theater-text placeholder-theater-text-muted focus:border-twitch-purple focus:ring-twitch-purple'
              : 'bg-white border-gray-300 text-gray-700 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500'
          } flex-1 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-opacity-50`}
        />
        <button
          onClick={sendMessage}
          className={`${
            isTheaterMode
              ? 'bg-twitch-purple hover:bg-twitch-purple-dark'
              : 'bg-green-600 hover:bg-green-700'
          } px-4 py-2 text-white border-none rounded-md cursor-pointer text-sm font-medium transition-colors`}
        >
          Send
        </button>
      </div>
    </div>
  );
}