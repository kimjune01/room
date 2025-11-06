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
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] ${message}${data ? ' ' + JSON.stringify(data) : ''}\n`;

    // Log to console
    console.log(message, data || '');

    // Get existing log
    let existingLog = localStorage.getItem(this.LOG_KEY) || '';

    // Append new entry
    existingLog += logEntry;

    // Trim if too large (keep last portion)
    if (existingLog.length > this.MAX_LOG_SIZE) {
      existingLog = existingLog.slice(-this.MAX_LOG_SIZE);
    }

    // Save to localStorage
    localStorage.setItem(this.LOG_KEY, existingLog);

    // Also try to send to backend for analysis (non-blocking)
    try {
      fetch('/api/debug-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timestamp, message, data })
      }).catch((error: Error) => {
        // Silently fail - backend logging is non-critical
        console.debug('Failed to send log to backend:', error.message);
      });
    } catch (error) {
      // Fetch not available or other error - silently ignore
      console.debug('Debug logging to backend unavailable');
    }
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