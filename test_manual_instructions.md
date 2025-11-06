# Manual Browser Test Instructions

## Setup
1. Backend server is running on http://localhost:8000
2. Frontend is running on http://localhost:5173

## Test Steps

### Test 1: Single User Connection
1. Open http://localhost:5173 in your browser
2. Enter room name: "testroom" (default)
3. Enter your name: "Alice"
4. Click "Connect"
5. Verify you see "Connected as: Alice"
6. Type a message and press Enter or click Send
7. Verify the message appears in the chat

### Test 2: Two Users in Same Room
1. Open http://localhost:5173 in Browser Tab 1
2. Connect as "Alice" to room "testroom"
3. Open http://localhost:5173 in Browser Tab 2 (or incognito window)
4. Connect as "Bob" to room "testroom"
5. Verify Alice's tab shows "Bob joined the room"
6. From Alice's tab: Send "Hello Bob!"
7. Verify Bob's tab receives the message
8. From Bob's tab: Send "Hi Alice!"
9. Verify Alice's tab receives the message

### Expected Results
- Messages from yourself appear on the right (blue background)
- Messages from others appear on the left (white background)
- Join/leave notifications appear centered in gray
- Both users can see each other's messages in real-time

## Current Status
✅ Backend WebSocket server is running
✅ Frontend React app is running
✅ Programmatic round-trip test passed
✅ Two clients can successfully exchange messages