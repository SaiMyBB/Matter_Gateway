# core/persistence.py
import json
import os
from threading import Lock

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "devices_state.json")

class Persistence:
    def __init__(self, path=STATE_FILE):
        self.path = path
        self.lock = Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def load_all(self):
        with self.lock:
            with open(self.path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
                except json.JSONDecodeError:
                    return {}

    def save_all(self, data: dict):
        with self.lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
