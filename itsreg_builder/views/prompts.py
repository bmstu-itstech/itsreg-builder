from __future__ import annotations

import inquirer3  # type: ignore[import-untyped]

from itsreg_builder.models.script import Node

MAIN_ACTIONS = [
    "Добавить узел",
    "Редактировать узел",
    "Удалить узел",
    "Добавить ребро",
    "Удалить ребро",
    "Добавить точку входа",
    "Удалить точку входа",
    "Показать граф",
    "Показать узел",
    "Выход",
]

PREDICATE_CHOICES = [
    ("Безусловный", "always"),
    ("Совпадение по тексту", "exact"),
    ("Совпадение по регулярному выражению", "regex"),
]

OPERATION_CHOICES = [
    ("noop   - без действия", "noop"),
    ("save   - сохранить ответ", "save"),
    ("append - добавить ответ в конец", "append"),
]


def select_main_action() -> str | None:
    try:
        result: str = inquirer3.list_input(message="Выберите действие", choices=MAIN_ACTIONS)
        return result
    except KeyboardInterrupt:
        return None


def text(message: str, default: str = "") -> str | None:
    try:
        result: str = inquirer3.text(message=message, default=default or None)
        return result
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
        result: bool = inquirer3.confirm(message=message, default=default)
        return result
    except KeyboardInterrupt:
        return False


def editor(message: str) -> str | None:
    try:
        result: str = inquirer3.editor(message=message)
        if result:
            return result.rstrip("\n")
        return None
    except KeyboardInterrupt:
        return None


def select(message: str, choices: list[str]) -> str | None:
    if not choices:
        return None
    try:
        result: str = inquirer3.list_input(message=message, choices=choices)
        return result
    except KeyboardInterrupt:
        return None


def select_predicate_type() -> str | None:
    try:
        result: str = inquirer3.list_input(
            message="Тип предиката",
            choices=PREDICATE_CHOICES,
        )
        return result
    except KeyboardInterrupt:
        return None


def select_operation() -> str | None:
    try:
        result: str = inquirer3.list_input(
            message="Действие при переходе по ребру",
            choices=OPERATION_CHOICES,
        )
        return result
    except KeyboardInterrupt:
        return None


def _node_choice(node: Node, max_title: int = 40) -> tuple[str, int]:
    title = node.title
    if len(title) > max_title:
        title = title[: max_title - 3] + "..."
    return (f"[{node.state}] {title}", node.state)


def select_node(nodes: list[Node], message: str = "Выберите узел") -> int | None:
    if not nodes:
        return None
    choices = [_node_choice(n) for n in sorted(nodes, key=lambda n: n.state)]
    try:
        result: int = inquirer3.list_input(message=message, choices=choices)
        return result
    except KeyboardInterrupt:
        return None
