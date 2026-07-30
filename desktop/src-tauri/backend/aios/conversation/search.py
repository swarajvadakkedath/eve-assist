"""Conversation search — full-text, fuzzy, and relevance-based."""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from aios.conversation.models import Conversation, Message, MessageRole


@dataclass
class SearchResult:
    conversation_id: str
    conversation_title: str
    message_id: str
    role: str
    content: str
    snippet: str
    score: float
    highlights: list[tuple[int, int]]


class ConversationSearch:
    def __init__(self):
        self._index: dict[str, list[dict]] = {}

    async def index_conversation(self, conversation: Conversation, messages: list[Message]):
        entries = []
        for msg in messages:
            entries.append({
                "conversation_id": conversation.id,
                "conversation_title": conversation.title,
                "message_id": msg.id,
                "role": msg.role.value if hasattr(msg.role, "value") else msg.role,
                "content": msg.content,
                "title": conversation.title,
                "tool_calls": [tc.tool_name for tc in (msg.tool_calls or [])],
            })
        self._index[conversation.id] = entries

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SearchResult]:
        if not query or len(query.strip()) < 1:
            return []

        query = query.lower().strip()
        results: list[SearchResult] = []

        for conv_id, entries in self._index.items():
            for entry in entries:
                score = self._calculate_score(query, entry)
                if score > 0:
                    highlights = self._find_highlights(query, entry["content"])
                    snippet = self._build_snippet(entry["content"], highlights, query)
                    results.append(SearchResult(
                        conversation_id=conv_id,
                        conversation_title=entry["title"],
                        message_id=entry["message_id"],
                        role=entry["role"],
                        content=entry["content"],
                        snippet=snippet,
                        score=score,
                        highlights=highlights,
                    ))

        results.sort(key=lambda r: (-r.score, r.conversation_title))
        return results[:limit]

    async def search_conversations(
        self,
        query: str,
        conversations: list[Conversation],
        messages_by_id: dict[str, list[Message]],
        limit: int = 20,
    ) -> list[SearchResult]:
        if not query:
            return []
        query = query.lower().strip()

        for conv in conversations:
            msgs = messages_by_id.get(conv.id, [])
            await self.index_conversation(conv, msgs)

        return await self.search(query, limit)

    def _calculate_score(self, query: str, entry: dict) -> float:
        score = 0.0
        title = entry.get("title", "").lower()
        content = entry.get("content", "").lower()
        role = entry.get("role", "")

        if query in title:
            score += 10.0
        if title.startswith(query):
            score += 5.0

        if query in content:
            score += 3.0
            appearances = content.count(query)
            score += min(appearances * 0.5, 5.0)

        ratio = SequenceMatcher(None, query, content[:len(query) * 3]).ratio()
        if ratio > 0.6:
            score += ratio * 2.0

        words = query.split()
        content_words = content.split()
        for word in words:
            for cw in content_words:
                if SequenceMatcher(None, word, cw).ratio() > 0.8:
                    score += 1.0
                    break

        if role == "user":
            score += 0.5

        return score

    def _find_highlights(self, query: str, content: str) -> list[tuple[int, int]]:
        highlights = []
        lower = content.lower()
        query_lower = query.lower()
        start = 0
        while True:
            idx = lower.find(query_lower, start)
            if idx == -1:
                break
            highlights.append((idx, idx + len(query)))
            start = idx + 1
        return highlights[:5]

    def _build_snippet(self, content: str, highlights: list[tuple[int, int]], query: str) -> str:
        if not highlights:
            idx = content.lower().find(query.lower())
            if idx == -1:
                return content[:150] + ("..." if len(content) > 150 else "")
            start = max(0, idx - 50)
            end = min(len(content), idx + 100)
            snippet = content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet = snippet + "..."
            return snippet

        hl_start = highlights[0][0]
        start = max(0, hl_start - 50)
        end = min(len(content), highlights[-1][1] + 100)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet

    async def clear_index(self, conversation_id: str | None = None):
        if conversation_id:
            self._index.pop(conversation_id, None)
        else:
            self._index.clear()
