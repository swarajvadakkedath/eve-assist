"""Pronunciation Dictionary — custom word pronunciations."""

from __future__ import annotations

import json
import time
import threading
from typing import Optional

from .models import PronunciationEntry


class PronunciationDictionary:
    """Manages custom word pronunciations.

    Supports technical terminology, names, abbreviations, and project names.
    All lookups are O(1) via hash map. Thread-safe.
    """

    def __init__(self):
        self._entries: dict[str, PronunciationEntry] = {}
        self._lock = threading.Lock()
        self._created_at = time.monotonic()
        self._lookup_count: int = 0

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def add(self, word: str, phonetic: str, *, language: str = "en",
            category: str = "custom", notes: str = "") -> PronunciationEntry:
        with self._lock:
            entry = PronunciationEntry(word=word, phonetic=phonetic, language=language,
                                       category=category, notes=notes)
            self._entries[word.lower()] = entry
            return entry

    def remove(self, word: str) -> bool:
        with self._lock:
            key = word.lower()
            if key in self._entries:
                del self._entries[key]
                return True
            return False

    def lookup(self, word: str) -> Optional[PronunciationEntry]:
        with self._lock:
            self._lookup_count += 1
            return self._entries.get(word.lower())

    def has(self, word: str) -> bool:
        with self._lock:
            return word.lower() in self._entries

    def get_all(self) -> list[PronunciationEntry]:
        with self._lock:
            return list(self._entries.values())

    def get_by_category(self, category: str) -> list[PronunciationEntry]:
        with self._lock:
            return [e for e in self._entries.values() if e.category == category]

    def get_by_language(self, language: str) -> list[PronunciationEntry]:
        with self._lock:
            return [e for e in self._entries.values() if e.language == language]

    def clear(self):
        with self._lock:
            self._entries.clear()

    def export_dict(self) -> dict:
        with self._lock:
            return {word: entry.to_dict() for word, entry in self._entries.items()}

    def import_dict(self, data: dict) -> int:
        count = 0
        with self._lock:
            for word, entry_data in data.items():
                entry = PronunciationEntry(**entry_data)
                self._entries[word.lower()] = entry
                count += 1
        return count

    def export_json(self) -> str:
        return json.dumps(self.export_dict(), indent=2)

    def import_json(self, json_str: str) -> int:
        data = json.loads(json_str)
        return self.import_dict(data)

    def load_defaults(self):
        defaults = {
            "typescript": {"phonetic": "TY-pah-skript", "category": "technology", "notes": "Programming language"},
            "next.js": {"phonetic": "NEXT-jayz", "category": "technology", "notes": "React framework"},
            "opencode": {"phonetic": "OPEN-kohd", "category": "project", "notes": "AI coding tool"},
            "groq": {"phonetic": "GROK", "category": "technology", "notes": "AI inference company"},
            "gemini": {"phonetic": "JEM-ih-nee", "category": "technology", "notes": "Google AI model"},
            "figma": {"phonetic": "FIG-mah", "category": "technology", "notes": "Design tool"},
            "ui/ux": {"phonetic": "you-eye-slash-you-ex", "category": "design", "notes": "Design disciplines"},
            "api": {"phonetic": "A-pah-eye", "category": "technology", "notes": "Application Programming Interface"},
            "json": {"phonetic": "JAY-sawn", "category": "technology", "notes": "Data format"},
            "yaml": {"phonetic": "YAH-mul", "category": "technology", "notes": "Data format"},
        }
        for word, data in defaults.items():
            if not self.has(word):
                self.add(word, data["phonetic"], category=data["category"], notes=data["notes"])

    def snapshot(self) -> dict:
        with self._lock:
            categories = {}
            for entry in self._entries.values():
                categories[entry.category] = categories.get(entry.category, 0) + 1
            return {
                "total_entries": len(self._entries),
                "lookup_count": self._lookup_count,
                "categories": categories,
            }

    def reset(self):
        with self._lock:
            self._entries.clear()
            self._lookup_count = 0
            self._created_at = time.monotonic()
