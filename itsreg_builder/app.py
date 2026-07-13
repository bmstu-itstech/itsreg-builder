from __future__ import annotations

from itsreg_builder.controllers.script_controller import ScriptController
from itsreg_builder.models.repository import ScriptRepository


class App:
    def __init__(self, file_path: str):
        repository = ScriptRepository(file_path)
        self.controller = ScriptController(repository)

    def run(self) -> None:
        self.controller.run()
