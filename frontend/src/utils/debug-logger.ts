// Debug logger that writes to localStorage for persistence
// Can be retrieved from browser console with: localStorage.getItem('youtube-debug-log')

// Extend Window interface for DebugLogger
declare global {
  interface Window {
    DebugLogger: typeof DebugLogger;
  }
}

export class DebugLogger {
  private static MAX_LOG_SIZE = 50000; // Max characters to store
  private static LOG_KEY = 'youtube-debug-log';

  static log(message: string, data?: unknown): void {
    // Temporarily disabled to reduce performance overhead
    // Only log to console for critical debugging
    if (message.includes('ERROR') || message.includes('CRITICAL')) {
      console.log(message, data || '');
    }

    // Disable localStorage and network logging for performance
    return;
  }

  static clear() {
    localStorage.removeItem(this.LOG_KEY);
    console.log('Debug log cleared');
  }

  static download() {
    const log = localStorage.getItem(this.LOG_KEY) || 'No logs available';
    const blob = new Blob([log], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `youtube-debug-${Date.now()}.log`;
    a.click();
    URL.revokeObjectURL(url);
  }

  static getLogs(): string {
    return localStorage.getItem(this.LOG_KEY) || 'No logs available';
  }
}

// Expose to window for easy access from console
if (typeof window !== 'undefined') {
  window.DebugLogger = DebugLogger;
  console.log('Debug logger available. Use: DebugLogger.getLogs(), DebugLogger.download(), DebugLogger.clear()');
}