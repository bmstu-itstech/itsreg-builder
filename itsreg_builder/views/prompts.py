from __future__ import annotations

import inquirer3


MAIN_ACTIONS = [
    "Add node",
    "Edit node",
    "Delete node",
    "Add edge",
    "Delete edge",
    "Add entry",
    "Delete entry",
    "Show script",
    "Show JSON",
    "Creation wizard",
    "Exit",
]

PREDICATE_CHOICES = [
    ("Always (any message)", "always"),
    ("Exact text match", "exact"),
    ("Regex pattern", "regex"),
]

OPERATION_CHOICES = [
    ("noop  - no action (menus, intermediate nodes)", "noop"),
    ("save  - save user response (overwrites)", "save"),
    ("append - append to previous (multi-select)", "append"),
]


def select_main_action() -> str | None:
    try:
        return inquirer3.list_input(message="Select action", choices=MAIN_ACTIONS)
    except KeyboardInterrupt:
        return None


def text(message: str, default: str = "") -> str | None:
    try:
        return inquirer3.text(message=message, default=default or None)
    except KeyboardInterrupt:
        return None


def integer(message: str, default: int = 1) -> int | None:
    raw = text(message, default=str(default))
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return default


def confirm(message: str, default: bool = False) -> bool:
    try:
        return inquirer3.confirm(message=message, default=default)
    except KeyboardInterrupt:
        return False


def editor(message: str) -> str | None:
    try:
        result = inquirer3.editor(message=message)
        if result:
            return result.rstrip("\n")
        return None
    except KeyboardInterrupt:
        return None


def select(message: str, choices: list[str]) -> str | None:
    if not choices:
        return None
    try:
        return inquirer3.list_input(message=message, choices=choices)
    except KeyboardInterrupt:
        return None


def select_predicate_type() -> str | None:
    try:
        return inquirer3.list_input(
            message="Predicate type",
            choices=PREDICATE_CHOICES,
        )
    except KeyboardInterrupt:
        return None


def select_operation() -> str | None:
    try:
        return inquirer3.list_input(
            message="Edge operation",
            choices=OPERATION_CHOICES,
        )
    except KeyboardInterrupt:
        return None


def select_node(states: list[int], message: str = "Select node") -> int | None:
    if not states:
        return None
    choices = [str(s) for s in sorted(states)]
    answer = select(message, choices)
    return int(answer) if answer else None
