# AEGIS1 Testing Guide

## Overview

AEGIS1 has multiple ways to test the system. Choose based on your needs:

| Method | Command | Use Case |
|--------|---------|----------|
| **Terminal (Text CLI)** | `python -m aegis terminal` | Direct backend testing, fastest iteration |
| **Web Dashboard** | `http://localhost:3001` | Visual UI, see transcription feed, health data |
| **Web Chat** | `http://localhost:3001` → Chat tab | Browser-based chat interface |
| **Hardware (ESP32)** | WebSocket to port 8000 | Real voice pendant testing |

---

## Quick Start: Terminal Testing (Recommended)

### Step 1: Start the AEGIS Backend Server

```bash
cd /Users/apple/Documents/aegis1
python -m aegis serve
```

**Expected Output:**
```
🚀 Starting AEGIS1 Bridge on 0.0.0.0:8000
INFO:     Started server process [12345]
INFO:     Application startup complete.
```

**Server running on:** `http://localhost:8000`

### Step 2: Open Another Terminal Tab

Start the interactive terminal client:

```bash
cd /Users/apple/Documents/aegis1
python -m aegis terminal
```

**Expected Output:**
```
🎤 AEGIS1 Terminal Client
Type your question or 'exit' to quit

You:
```

### Step 3: Test Conversations

Type any message and press Enter. AEGIS will respond with streaming text.

**Test Examples:**

#### Test 1: Simple Health Question
```
You: How did I sleep this week?
AEGIS: Based on your data, you averaged 6.8 hours of sleep over the last 7 days...
```
Expected response time: <500ms

#### Test 2: Spending Query
```
You: What's my spending breakdown?
AEGIS: Your spending this month totals $1,240 across categories...
```
Expected response time: <500ms

#### Test 3: Complex Analysis (Triggers Opus)
```
You: Why am I tired on weekdays and what should I do about it?
AEGIS: [Taking longer... using Opus for deep analysis]
...your weekday fatigue correlates with 2 fewer hours of sleep...
```
Expected response time: 1-2 seconds

#### Test 4: Create a Goal
```
You: Help me train for a 5K run
AEGIS: Based on your current activity level (8,234 steps/day average)...
```

#### Test 5: Reset Conversation
```
You: /reset
AEGIS: Conversation reset.
```

### Step 4: Exit Terminal Client

```
You: exit
👋 Goodbye!
```

---

## Web Dashboard Testing

### Start All Services

**Terminal 1: Start AEGIS Backend**
```bash
python -m aegis serve
```

**Terminal 2: Start Frontend Server**
```bash
cd /Users/apple/Documents/aegis1/static
python -m http.server 3001
```

### Access Dashboard

1. Open browser: `http://localhost:3001`
2. Click **Chat** tab
3. Type a message (same examples as above)
4. Watch **Dashboard** tab to see:
   - Real-time conversation feed (You | AEGIS)
   - Backend connection status (8000)
   - Bridge connection status (3000)

---

## Seeding Demo Data

AEGIS comes with 30 days of demo health and spending data:

```bash
python -m aegis seed
```

This populates:
- Sleep logs (6-8 hours/night)
- Exercise minutes (20-60/day)
- Mood scores (6-9/10)
- Expenses by category (Food, Transport, Coffee, etc.)

---

## Backend Health Check

Verify the backend is running:

```bash
python -m aegis health
```

**Expected Output:**
```
✅ Server healthy: {'status': 'ok', 'service': 'aegis1-bridge'}
```

---

## File Reference

| File | Purpose | How to Use |
|------|---------|-----------|
| `aegis/__main__.py` | CLI entry point with all commands | `python -m aegis [command]` |
| `aegis/main.py` | FastAPI WebSocket server | Started by `serve` command |
| `aegis/claude_client.py` | Claude API integration | Runs automatically in server |
| `aegis/config.py` | Configuration & settings | Edit for tuning |
| `static/index.html` | Web UI (all-in-one) | Access on port 3001 |

---

## Testing Checklist

### Backend
- [ ] `python -m aegis serve` starts without errors
- [ ] `python -m aegis health` returns ok
- [ ] `python -m aegis terminal` connects
- [ ] Type "How did I sleep?" → Get response <500ms
- [ ] Type "Why am I tired?" → Uses Opus (1-2s)
- [ ] Type "/reset" → Conversation clears

### Frontend (Web)
- [ ] `http://localhost:3001` loads landing page
- [ ] Click Chat tab → Input appears
- [ ] Type message → Sends and gets response
- [ ] Click Dashboard tab → Shows conversation feed
- [ ] Backend (8000) shows connected
- [ ] Bridge (3000) shows connection status

### Data
- [ ] Database has demo health data (7 days minimum)
- [ ] Spending data shows in responses
- [ ] Sleep/mood correlations detected

---

## Performance Targets

| Operation | Target | Actual |
|-----------|--------|--------|
| Haiku response | <500ms | - |
| Opus response | 1-2s | - |
| TTS latency | <100ms/sentence | - |
| STT latency | 200-400ms | - |
| Dashboard update | <50ms | - |

---

## Troubleshooting

### "Connection refused" on terminal
```
❌ Could not connect to server at ws://localhost:8000/ws/text
```
**Fix:** Make sure `python -m aegis serve` is running in another terminal

### "Module not found: aegis"
```bash
cd /Users/apple/Documents/aegis1
python -m aegis serve  # Use full path or cd first
```

### "No such table: health_logs"
```bash
python -m aegis seed   # Populate demo data
```

### Slow responses
- Check if backend is running: `python -m aegis health`
- Check ANTHROPIC_API_KEY in `.env`
- Verify Claude API is accessible

---

## Next Steps After Testing

1. **Hardware Testing:** Connect real ESP32 pendant to `/ws/audio` endpoint
2. **Real Data:** Import actual Apple Health XML via `python -m aegis import_health`
3. **Production:** Deploy to cloud (AWS, Heroku)
4. **Demo Video:** Record terminal + dashboard interactions

---

## Commands Reference

```bash
# Start backend server on port 8000
python -m aegis serve

# Interactive terminal client
python -m aegis terminal

# Seed demo data (30 days)
python -m aegis seed

# Health check
python -m aegis health

# Import Apple Health (Phase 2)
python -m aegis import_health /path/to/export.xml

# Version info
python -m aegis --version
```

---

## Architecture During Testing

```
┌─────────────────────────────────────────────────────────┐
│                    Your Machine                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Terminal 1: AEGIS Backend (Port 8000)                │
│  └─ python -m aegis serve                             │
│     ├─ /ws/text (chat endpoint)                       │
│     ├─ /ws/audio (hardware audio)                     │
│     └─ SQLite DB (health + expenses)                  │
│                                                         │
│  Terminal 2: Frontend Server (Port 3001)              │
│  └─ python -m http.server 3001                        │
│     └─ Serves static/index.html (UI)                  │
│                                                         │
│  Terminal 3: Test Client                              │
│  └─ python -m aegis terminal                          │
│     ├─ Connects to ws://localhost:8000/ws/text        │
│     └─ Shows streaming responses                      │
│                                                         │
│  Browser: http://localhost:3001                       │
│  └─ Dashboard shows conversation live                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Success Criteria

Testing is complete when:

✅ Terminal responds to all 5 test queries
✅ Response times meet targets (Haiku <500ms, Opus 1-2s)
✅ Dashboard shows live conversation feed
✅ Backend & Bridge show connected status
✅ No errors in server logs
✅ Database queries work without issues

**You're ready for submission!**
