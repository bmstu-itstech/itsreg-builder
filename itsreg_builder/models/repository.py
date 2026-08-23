from __future__ import annotations

import json
from pathlib import Path

from itsreg_builder.models.script import Script


class ScriptRepository:
    def __init__(self, file_path: str):
        self.path = Path(file_path)

    def load(self) -> Script | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return Script.model_validate(data)

    def save(self, script: Script) -> None:
        data = script.model_dump(mode="json")
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
