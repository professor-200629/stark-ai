"""
STARK Memory Module
Persistent JSON-based long-term memory.
"""

import json
import os
from datetime import datetime
import config


class Memory:
    def __init__(self):
        self.path = config.MEMORY_FILE
        self._data = self._load()

    # ── Private ───────────────────────────────────────────────────────────────
    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "user":          {},
            "preferences":   {},
            "history":       [],
            "reminders":     [],
            "notes":         {},
            "health":        {},
            "last_activity": None,
        }

    def _save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────
    def set(self, key: str, value) -> None:
        """Store any value under a top-level key."""
        self._data[key] = value
        self._save()

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def update_user(self, **kwargs) -> None:
        self._data["user"].update(kwargs)
        self._save()

    def add_history(self, role: str, content: str) -> None:
        self._data["history"].append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep only last 100 exchanges
        if len(self._data["history"]) > 100:
            self._data["history"] = self._data["history"][-100:]
        self._save()

    def get_recent_history(self, n: int = 10) -> list:
        """Return last n exchanges as [{role, content}] for Anthropic API."""
        recent = self._data["history"][-n * 2:]
        return [{"role": h["role"], "content": h["content"]} for h in recent]

    def add_note(self, title: str, content: str) -> None:
        self._data["notes"][title] = {
            "content":   content,
            "created":   datetime.now().isoformat(),
        }
        self._save()

    def summary(self) -> str:
        u = self._data.get("user", {})
        p = self._data.get("preferences", {})
        lines = ["Known about the user:"]
        for k, v in u.items():
            lines.append(f"  {k}: {v}")
        for k, v in p.items():
            lines.append(f"  preference – {k}: {v}")
        return "\n".join(lines) if len(lines) > 1 else "No user data stored yet."
