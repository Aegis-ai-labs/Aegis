# AEGIS1 Demo Script — 3 Minutes

## Setup (Before Demo)
1. Start bridge: `python -m bridge.main`
2. Open dashboard: `http://localhost:8000`
3. Connect ESP32 or prepare test_terminal.py
4. Position: Split screen (person + dashboard)

---

## Demo Flow (3:00 total)

### 0:00 - Opening (15 sec)
**Say:** "This is AEGIS1 — an AI voice pendant that makes health and wealth advice contextually intelligent by understanding your body."

**Action:** Show pendant (or mic setup)

---

### 0:15 - Query 1: Simple Health Query (30 sec)
**User:** "I only got 5 hours of sleep last night, feeling groggy."

**What Happens:**
- Dashboard shows: User message
- Haiku badge appears (~150ms)
- Tool call: `log_health(metric="sleep_hours", value=5.0)`
- Response: "Logged 5 hours — that's below your 6.2 hour average this week. Your mood tends to be lower on less sleep. Try to catch up tonight."

**Point Out:** 
- Notice the speed (Haiku, <500ms)
- Tool automatically logged the data
- Context-aware (knows weekly average, sleep-mood correlation)

---

### 0:45 - Query 2: Cross-Domain Intelligence (30 sec)
**User:** "I just spent $12 on a large coffee."

**What Happens:**
- Tool call: `track_expense(amount=12, category="food")`
- Response: "Got it, $12 on coffee — that brings you to $87 in food spending this week. Rough night's sleep and a caffeine boost, that tracks."

**Point Out:**
- Cross-domain awareness (health → spending connection)
- Proactive insight without being asked
- Human-like contextual understanding

---

### 1:15 - Query 3: Deep Analysis with Opus (45 sec)
**User:** "Why have I been so tired on weekdays?"

**What Happens:**
- Dashboard shows: "THINKING" badge (Opus 4.6 with interleaved thinking)
- Tool call: `analyze_health_patterns(query="weekday fatigue")`
- Tool call: `get_health_context(days=7)`
- Response: "Looking at your data, you're averaging 6 hours of sleep on weekdays versus 7.9 hours on weekends — nearly a 2-hour deficit. Your mood scores drop from 3.8 on weekends to 2.5 on weekdays. This pattern suggests chronic weekday sleep debt. Consider moving your weeknight bedtime 30 minutes earlier."

**Point Out:**
- Opus 4.6 deep thinking (visible in logs/dashboard)
- Multiple tool calls for comprehensive analysis
- Data-driven, actionable advice
- THE wow moment

---

### 2:00 - Query 4: Body-Aware Personalization (30 sec)
**User:** "I want to train for a 5K race."

**What Happens:**
- Tool calls: `get_health_context()`, `analyze_health_patterns()`
- Response: "Based on your current fitness, you're averaging 10 minutes of exercise on weekdays and 45 on weekends. For 5K training, aim for 20-30 minutes 4 times per week. Given your weekday sleep constraints, I'd suggest lunchtime walks Monday-Thursday to avoid evening fatigue."

**Point Out:**
- Advice is personalized to HIS body
- Considers his actual sleep patterns
- Not generic — truly contextual
- This is the future of AI assistants

---

### 2:30 - Technical Credibility (15 sec)
**Show Dashboard:**
- Haiku: ~150ms latency
- Opus: ~2s with thinking
- 7 tools working
- Real-time updates

**Say:** "All running locally, fully private, on an ESP32 microcontroller."

---

### 2:45 - Impact Framing (10 sec)
**Say:** "Imagine: Your doctor, your financial advisor, your personal trainer — all in one voice assistant that actually knows YOU. That's contextual intelligence for everyone."

---

### 2:55 - Close (5 sec)
**User:** "Good night, Aegis."

**Aegis:** "Sleep well — aim for 7+ hours. Your mood will thank you."

**END**

---

## Backup Queries (if needed)

- "How much did I spend on food this week?"
- "Compare my sleep to last week."
- "Help me save $5000 in 6 months."
- "What's the relationship between my exercise and sleep?"

---

## Key Messages

1. **Speed:** Haiku responds in <500ms (fast enough for voice)
2. **Depth:** Opus thinks deeply with interleaved thinking (THE Opus 4.6 showcase)
3. **Context:** Not generic advice — personalized to YOUR body and YOUR data
4. **Cross-domain:** Health and wealth interconnected (sleep → spending, mood → behavior)

## Technical Highlights
- True streaming (messages.stream())
- Interleaved thinking beta
- 7 tools (3 health, 3 wealth, 1 insight)
- Prompt caching for efficiency
- Real-time dashboard
- All in <2,200 lines of code
