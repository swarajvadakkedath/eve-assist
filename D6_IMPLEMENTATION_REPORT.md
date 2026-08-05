# Sprint D6 — Continuous Conversation

**Date:** 2026-08-05
**Status:** COMPLETE
**Tests:** 70/70 (provider_framework)

## Summary

Sprint D6 implements the continuous conversation subsystem for VoiceOS+. The module manages multi-turn conversations with follow-up detection, barge-in interrupt, timeout management, context tracking, and session lifecycle — enabling EVE to hold natural back-and-forth conversations without re-invocation.

## Files Implemented

| File | Purpose |
|------|---------|
| `voice/conversation/__init__.py` | Package exports |
| `voice/conversation/events.py` | Turn, ConversationEvent, ConversationEventType (12 types) |
| `voice/conversation/state.py` | ConversationState enum (8 states), CONVERSATION_TRANSITIONS, can_transition() |
| `voice/conversation/session.py` | ConversationSession, ConversationSessionConfig, ConversationSessionStats, ConvEvent |
| `voice/conversation/metrics.py` | ConversationMetrics, ConversationMetricsSnapshot (percentiles, durations) |
| `voice/conversation/manager.py` | ConversationSessionManager, TurnManager, ConversationManagerConfig, TurnState, ManagerEvent |
| `tests/provider_framework/test_conversation.py` | 70 tests across 11 test classes |

## Architecture

### State Machine
```
IDLE → LISTENING → PROCESSING → SPEAKING → WAITING_FOR_FOLLOW_UP
                    ↑              ↓              ↓
                    ←──────────────←──────────────← (follow-up / resume)
                                                           ↓
                                                    LISTENING / TIMED_OUT / ENDED
```

8 conversation states: IDLE, LISTENING, PROCESSING, SPEAKING, WAITING_FOR_FOLLOW_UP, PAUSED, TIMED_OUT, ENDED.

### TurnManager
- 5-state turn-level state machine: IDLE → LISTENING → PROCESSING → SPEAKING → WAITING
- Timeout detection: follow-up timeout, conversation timeout
- Barge-in interrupt support

### ConversationSessionManager
- Session lifecycle: start_conversation / end_conversation
- Turn management: begin_turn / complete_turn
- Speaking control: start_speaking / stop_speaking / resume_listening
- Interrupt: barge-in with configurable enable/disable
- Context: key-value store per session
- Events: synchronous handler dispatch (SESSION_STARTED, SESSION_ENDED, TURN_STARTED, TURN_COMPLETED, BARGE_IN, LISTENING_RESUMED)
- Metrics: delegation to ConversationMetrics
- Thread-safe: all public methods protected by threading.Lock

### ConversationSessionConfig
- silence_timeout_s: 1.5s default
- follow_up_timeout_s: 5.0s default
- conversation_timeout_s: 300.0s default
- max_turns: 100
- enable_barge_in: true
- enable_follow_ups: true

## Key Design Decisions

1. **Synchronous-first design**: All classes work without an event loop. Session events use `asyncio.get_running_loop()` with silent fallback when no loop is available — enables both sync tests and async production use.

2. **Follow-up detection**: When begin_turn is called while in WAITING_FOR_FOLLOW_UP state, the turn is automatically marked `is_follow_up=True` and the session's follow_up_count increments. State transitions directly from WAITING_FOR_FOLLOW_UP → PROCESSING.

3. **Barge-in**: When enabled, interrupt() transitions SPEAKING → LISTENING and marks the current turn as interrupted. When disabled, interrupt() is a no-op.

4. **Session cleanup**: Sessions are removed from the manager's internal dict when ended, preventing memory leaks in long-running instances.

5. **Manager vs Session separation**: ConversationSession handles individual session lifecycle. ConversationSessionManager orchestrates sessions, provides global metrics, and dispatches events. TurnManager handles turn-level state at the manager level.

## Test Coverage

- **TestTurn** (6): creation, params, latency, to_dict, thread safety
- **TestConversationEvent** (3): creation, all event types, to_dict
- **TestConversationState** (5): all states, valid/invalid transitions, table completeness, ended is terminal
- **TestConversationSessionConfig** (1): defaults
- **TestConversationSession** (12): lifecycle, begin/complete turn, speaking cycle, follow-up, interruption, timeout, end, stats, context, uptime, events, thread safety
- **TestConversationMetrics** (10): basics, conversation end, turn tracking, follow-ups, interruptions, timeouts, snapshot, reset, latency tracking, empty snapshot
- **TestTurnManager** (11): initial state, start listening, user speaking, processing complete, eve done, invalid transition, barge-in, follow-up timeout, conversation timeout, no timeout, reset
- **TestConversationManagerConfig** (2): defaults, to_dict
- **TestConversationSessionManager** (14): start/end, begin/complete turn, start/stop speaking, resume listening, interrupt, barge-in disabled, follow-up timeout, conversation timeout, set/get context, snapshot, event handlers, reset, no session actions, custom timeouts, thread safety
- **TestConversationIntegration** (4): multi-turn, barge-in, context, multiple sessions

## Desktop Mirror

All 6 source files mirrored to `desktop/src-tauri/backend/aios/voice/conversation/` with byte-identical parity verified via `git diff --no-index`.
