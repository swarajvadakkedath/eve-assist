"""Conversation State — state machine for conversation lifecycle."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ConversationState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    WAITING_FOR_FOLLOW_UP = "waiting_for_follow_up"
    PAUSED = "paused"
    TIMED_OUT = "timed_out"
    ENDED = "ended"


CONVERSATION_TRANSITIONS = {
    ConversationState.IDLE: {ConversationState.LISTENING, ConversationState.ENDED},
    ConversationState.LISTENING: {
        ConversationState.PROCESSING, ConversationState.WAITING_FOR_FOLLOW_UP,
        ConversationState.PAUSED, ConversationState.TIMED_OUT, ConversationState.ENDED,
    },
    ConversationState.PROCESSING: {
        ConversationState.SPEAKING, ConversationState.LISTENING,
        ConversationState.ENDED,
    },
    ConversationState.SPEAKING: {
        ConversationState.LISTENING, ConversationState.WAITING_FOR_FOLLOW_UP,
        ConversationState.PAUSED, ConversationState.ENDED,
    },
    ConversationState.WAITING_FOR_FOLLOW_UP: {
        ConversationState.LISTENING, ConversationState.PROCESSING,
        ConversationState.TIMED_OUT, ConversationState.ENDED,
    },
    ConversationState.PAUSED: {
        ConversationState.LISTENING, ConversationState.ENDED,
    },
    ConversationState.TIMED_OUT: {ConversationState.IDLE, ConversationState.ENDED},
    ConversationState.ENDED: set(),
}


def can_transition(from_state: ConversationState, to_state: ConversationState) -> bool:
    valid = CONVERSATION_TRANSITIONS.get(from_state, set())
    return to_state in valid
