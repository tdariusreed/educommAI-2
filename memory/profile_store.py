"""One SQLite row per student: their profile as JSON. One connection, schema created once."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from core.models import PROFILE_FIELDS, Profile, normalize_updates
from core.safety import scrub_pii


class ProfileStore:
    def __init__(self, db_path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            self._conn.commit()

    def _read(self, user_id: str) -> dict:
        with self._lock:
            row = self._conn.execute("SELECT data FROM profiles WHERE user_id=?", (user_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def _write(self, user_id: str, data: dict) -> None:
        with self._lock:
            if data:
                self._conn.execute("INSERT INTO profiles (user_id, data) VALUES (?,?) "
                                   "ON CONFLICT(user_id) DO UPDATE SET data=excluded.data", (user_id, json.dumps(data)))
            else:
                self._conn.execute("DELETE FROM profiles WHERE user_id=?", (user_id,))
            self._conn.commit()

    def load(self, user_id: str) -> Profile:
        return Profile.from_dict(self._read(user_id))

    def fields(self, user_id: str) -> list[tuple]:
        """[(key, value)] in display order, for the 'what I know about you' panel."""
        data = self._read(user_id)
        return [(k, data[k]) for k in PROFILE_FIELDS if k in data]

    def set_fields(self, user_id: str, updates: dict, replace: bool = False) -> dict:
        """Apply updates (interests accumulate unless replace=True). Returns what changed."""
        updates = normalize_updates(updates)
        for key, value in updates.items():  # free text can hold phone numbers / addresses; never store or search them
            if isinstance(value, str):
                updates[key] = scrub_pii(value)[0]
            elif isinstance(value, list):
                updates[key] = [scrub_pii(v)[0] for v in value]
        data = self._read(user_id)
        changed = {}
        for key, value in updates.items():
            if key == "interests" and data.get("interests") and not replace:
                have = {i.lower() for i in data["interests"]}
                value = (data["interests"] + [i for i in value if i.lower() not in have])[:10]
            if data.get(key) != value:
                data[key] = value
                changed[key] = value
        if changed:
            self._write(user_id, data)
        return changed

    def delete_field(self, user_id: str, key: str) -> None:
        data = self._read(user_id)
        if data.pop(key, None) is not None:
            self._write(user_id, data)

    def delete_all(self, user_id: str) -> None:
        self._write(user_id, {})
