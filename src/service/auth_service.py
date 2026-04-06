from __future__ import annotations

import json
import os
from typing import Dict, Optional


class AuthService:
    def __init__(self, users_file: str = "storage/users.json") -> None:
        self.users_file = users_file

    def _load_users(self) -> list[dict]:
        if not os.path.exists(self.users_file):
            return []

        with open(self.users_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        return data

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        username = username.strip()
        password = password.strip()

        if not username or not password:
            return None

        for user in self._load_users():
            if (
                user.get("username", "").strip() == username
                and user.get("password", "").strip() == password
            ):
                return {
                    "username": user.get("username", ""),
                    "role": user.get("role", "operator"),
                    "display_name": user.get("display_name", user.get("username", "")),
                }

        return None