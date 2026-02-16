# Aegis Task Management - Demo Guide

## Quick Start

### 1. Verify Implementation
```bash
cd /Users/apple/Documents/aegis1
python verify_aegis_tasks.py
# Should output: ✓ ALL VERIFICATIONS PASSED
```

### 2. Start the Server
```bash
python -m aegis.main
# Should log:
# ✓ Database initialized
# ✓ TaskExecutor started in background
```

### 3. Demo Scenarios

---

## Demo Scenario 1: Create a One-Shot Task

**Duration:** 2 minutes

**Setup:**
- Server running on `ws://localhost:8000/ws/text`

**Steps:**

1. Connect to text WebSocket
```
Send: {"text": "Set a reminder to take a break in 2 minutes"}
```

2. Claude responds:
```
Claude: "I'll create a reminder for you to take a break in 2 minutes."
```

3. Claude calls tool:
```
Tool: create_background_task(
  title="Take a break reminder",
  description="Remind user to take a 5-minute break and stretch",
  priority=5,
  task_type="oneshot"
)
→ Response: {"success": true, "task_id": 1}
```

4. Wait a few seconds for executor to pick it up

5. Query the task:
```
Send: {"text": "Check the status of task 1"}
```

6. Claude responds:
```
Claude: "I'll check that task for you."
Tool: get_task_status(task_id=1)
→ Response: {"success": true, "task": {
    "id": 1,
    "title": "Take a break reminder",
    "status": "completed",  ← Changed from pending!
    "result": "Reminder executed",
    ...
}}
Claude: "Your reminder task has been completed. The system executed the reminder for you."
```

**Key Demo Points:**
- ✓ Task was created and stored
- ✓ Executor picked it up automatically
- ✓ Task executed and status was updated
- ✓ Status is persistent (would survive server restart)

---

## Demo Scenario 2: Create a Daily Recurring Task

**Duration:** 3 minutes

**Steps:**

1. Create daily task:
```
Send: {"text": "I want to be reminded to check my health metrics every day at 7am"}
```

2. Claude responds and creates:
```
Tool: create_background_task(
  title="Daily health check reminder",
  description="Remind user to log daily health metrics (sleep, mood, exercise)",
  task_type="recurring",
  schedule={"type": "daily", "time": "07:00"}
)
→ Response: {"success": true, "task_id": 2}
```

3. Show that it's scheduled:
```
Send: {"text": "What recurring tasks do I have?"}
```

4. Claude queries:
```
Tool: list_all_tasks(status="pending")
→ Returns tasks with task_id=2 status="pending" task_type="recurring"
```

5. Claude explains:
```
Claude: "You have 1 recurring task: 'Daily health check reminder' 
scheduled for 7:00 AM every day. The system will automatically 
remind you at that time each day."
```

**Key Demo Points:**
- ✓ Recurring task persisted with schedule
- ✓ Can query tasks and see they're stored
- ✓ Executor will run this daily at 7am
- ✓ No manual intervention needed

---

## Demo Scenario 3: Monitor Task Execution

**Duration:** 2 minutes

**Setup:**
- WebSocket client connected to `/ws/tasks`

**Steps:**

1. Create a new task:
```
Send (to /ws/text): {"text": "Log that I drank 8 glasses of water today"}
```

2. Claude creates task:
```
Tool: create_background_task(
  title="Log water intake",
  description="Log 8 glasses of water as health metric",
  task_type="oneshot"
)
```

3. Watch `/ws/tasks` WebSocket for updates:
```
Receive: {
  "type": "task_update",
  "pending": [{"id": 3, "title": "Log water intake", "status": "pending", ...}],
  "in_progress": [],
  "completed": [],
  "timestamp": "2026-02-16T..."
}
```

4. After a few seconds (executor polls and executes):
```
Receive: {
  "type": "task_update",
  "pending": [],
  "in_progress": [],
  "completed": [{"id": 3, "title": "Log water intake", "status": "completed", 
                 "result": "Logged 8 glasses of water", ...}],
  "timestamp": "2026-02-16T..."
}
```

**Key Demo Points:**
- ✓ Task transitions from pending → completed in real-time
- ✓ WebSocket provides live monitoring
- ✓ Task execution happened in background
- ✓ Result was captured and stored

---

## Demo Scenario 4: Show Autonomous Execution

**Duration:** 4 minutes

**Setup:**
- Server running
- ESP32 hardware connected (or simulate with text)
- Two browser tabs/clients watching `/ws/tasks`

**Steps:**

1. Create a scheduled task at a future time:
```
Send: {"text": "Remind me to exercise in 1 minute with a sound"}
```

2. Claude creates task:
```
Tool: create_background_task(
  title="Exercise reminder",
  description="Play a reminder sound and ask user to exercise",
  task_type="scheduled",
  schedule={"type": "daily", "time": "HH:MM"}  ← Set to ~1 minute from now
)
```

3. Watch `/ws/tasks` WebSocket:
```
First update: Task in "pending" list
↓ (wait up to 1 minute)
Second update: Task moves to "in_progress"
↓ (executor runs, Claude plays sound via TTS)
Third update: Task moves to "completed" with result
```

4. Show the completed task details:
```
Send: {"text": "Show me all completed tasks"}

Claude: list_all_tasks(status="completed")
→ Shows exercise reminder was executed at the scheduled time
```

**Key Demo Points:**
- ✓ Task ran autonomously at scheduled time
- ✓ No manual trigger needed
- ✓ System executed tool (TTS) automatically
- ✓ Result captured and available for user query

---

## Advanced Demo: Task Persistence

**Duration:** 2 minutes

**Steps:**

1. Create a task:
```
Send: {"text": "Create a task to remind me weekly"}

Tool: create_background_task(
  title="Weekly review",
  description="Remind me to review my health and expenses",
  task_type="recurring",
  schedule={"type": "weekly", "day": "sunday", "time": "19:00"}
)
```

2. Stop the server:
```bash
# Press Ctrl+C in terminal running aegis
```

3. Verify data persisted to database:
```bash
python -c "
from aegis.task_manager import TaskManager
import asyncio

async def check():
    manager = TaskManager()
    tasks = await manager.list_tasks()
    print(f'Found {len(tasks)} tasks in database')
    for task in tasks:
        print(f'  - {task[\"title\"]}: {task[\"status\"]}')

asyncio.run(check())
"
```

4. Restart server:
```bash
python -m aegis.main
# Logs: ✓ TaskExecutor started in background
```

5. Query tasks:
```
Send: {"text": "What tasks do I have?"}

Claude: list_all_tasks()
→ Shows all tasks are still there!
```

**Key Demo Points:**
- ✓ Tasks persisted to SQLite database
- ✓ Survived server restart
- ✓ Tasks ready to execute again
- ✓ True persistent state

---

## Architecture Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    User (ESP32 or Client)                     │
└──────────────────────────────────────────┬───────────────────┘
                                           │
                                   /ws/text or /ws/audio
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Main Server                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User text → Claude → Tool call → dispatch_tool()           │
│                                       │                      │
│              ┌─────────────────────────┘                     │
│              │                                               │
│              ▼                                               │
│    create_background_task                                    │
│    get_task_status        → TaskManager → SQLite Database    │
│    list_all_tasks                         Tasks Table        │
│              │                                               │
│              └──────────┬──────────────────┐                │
│                         │                  │                │
└─────────────────────────┼──────────────────┼────────────────┘
                          │                  │
                  ┌───────▼─────┐    ┌──────▼──────┐
                  │ TaskExecutor │    │ WebSocket  │
                  │              │    │ /ws/tasks  │
                  │ - Polls for  │    │            │
                  │   pending    │    │ Broadcasts│
                  │ - Runs async │    │ updates   │
                  │   tasks      │    │ every 5s  │
                  └──────────────┘    └────────────┘
```

---

## Testing Without Hardware

If you don't have ESP32 hardware connected:

1. Use text WebSocket (`/ws/text`) instead of audio WebSocket
2. Tasks execute the same way
3. For demo of autonomous execution, you can:
   - Set a task to run in 1 minute
   - Watch it execute on the monitor WebSocket
   - No hardware needed

---

## Key Files for Demo

- `verify_aegis_tasks.py` - Run this first to verify everything works
- `AEGIS_TASK_MANAGEMENT_IMPLEMENTATION.md` - Detailed technical documentation
- `aegis/executor.py` - Background task executor (check logs here)
- `aegis/main.py` - Server integration (shows /ws/tasks endpoint)

---

## Troubleshooting

### Tasks not executing
1. Check that executor started: Look for "✓ TaskExecutor started" in logs
2. Check that task status is "pending": Use `get_task_status`
3. Check logs for errors in `_execute_task` method

### WebSocket not receiving updates
1. Verify `/ws/tasks` endpoint is listening
2. Check that connection is open
3. Verify client is receiving JSON every 5 seconds

### Tasks not persisting
1. Check that SQLite database file exists: `aegis1.db`
2. Verify tasks table has data: `select count(*) from tasks;`
3. Check that transactions are being committed

---

## Demo Script (Copy-Paste Ready)

```bash
# 1. Verify everything works
python verify_aegis_tasks.py

# 2. Start server
python -m aegis.main &

# 3. In another terminal, test the API
python -c "
import asyncio
import json
from aegis.task_manager import TaskManager

async def demo():
    manager = TaskManager()
    
    # Create task
    task_id = await manager.create_task(
        'Demo Task',
        'This is a demo task',
        priority=5
    )
    print(f'Created task {task_id}')
    
    # List tasks
    tasks = await manager.list_tasks()
    print(f'Total tasks: {len(tasks)}')
    
    # Update status
    await manager.update_status(task_id, 'completed', result='Demo completed')
    
    # Get updated task
    task = await manager.get_task(task_id)
    print(f'Task status: {task[\"status\"]}')

asyncio.run(demo())
"
```

---

**Ready to demo! ✓**
