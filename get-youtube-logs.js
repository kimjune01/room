#!/usr/bin/env node

// Script to retrieve YouTube debug logs from browser localStorage
// Usage:
// 1. Copy this entire script
// 2. Open browser console where the app is running
// 3. Paste and run the script
// 4. Logs will be downloaded as a file

// Run this in the browser console:
console.log(`
==================================================
YOUTUBE DEBUG LOG RETRIEVAL SCRIPT
==================================================

To download logs as a file, run:
  DebugLogger.download()

To view logs in console, run:
  console.log(DebugLogger.getLogs())

To clear logs, run:
  DebugLogger.clear()

To copy logs to clipboard, run:
  copy(DebugLogger.getLogs())

Current log size: ${(localStorage.getItem('youtube-debug-log') || '').length} characters
==================================================
`);

// Automatically show last 50 lines
const logs = localStorage.getItem('youtube-debug-log') || '';
const lines = logs.split('\n');
const last50 = lines.slice(-50).join('\n');
console.log('Last 50 log entries:\n' + last50);