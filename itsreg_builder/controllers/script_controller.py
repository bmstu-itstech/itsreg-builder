from __future__ import annotations

from collections.abc import Callable
from typing import Literal, cast

from itsreg_builder.models.repository import ScriptRepository
from itsreg_builder.models.script import (
    AlwaysPredicate,
    Edge,
    Entry,
    ExactPredicate,
    Message,
    Node,
    Predicate,
    RegexPredicate,
    Script,
)
from itsreg_builder.views import display, prompts


class ScriptController:
    def __init__(self, repository: ScriptRepository) -> None:
        self.repo = repository
        self.script: Script = Script(desc="")

    def run(self) -> None:
        loaded = self.repo.load()

        if loaded is None:
            display.info("Сценарий не найден. Создание нового...\n")
            desc = prompts.text("Описание сценария", default="Сценарий для бота") or ""
            self.script = Script(desc=desc)
            self._save()
            display.success("Сценарий создан!")
        else:
            self.script = loaded
            display.success(f"Загружен сценарий из файла {self.repo.path}")

        display.show_header(self.script)
        self._main_loop()

    # -- main loop --

    def _main_loop(self) -> None:
        handlers: dict[str, Callable[[], None]] = {
            "Добавить узел": self._add_node,
            "Редактировать узел": self._edit_node,
            "Удалить узел": self._delete_node,
            "Добавить ребро": self._add_edge,
            "Удалить ребро": self._delete_edge,
            "Добавить точку входа": self._add_entry,
            "Удалить точку входа": self._delete_entry,
            "Показать граф": self._show_graph,
            "Показать узел": self._view_node,
        }

        while True:
            action = prompts.select_main_action()
            if action is None or action == "Выход":
                display.info("Завершение работы...")
                break
            handler = handlers.get(action)
            if handler:
                try:
                    handler()
                except Exception as e:
                    display.error(f"Ошибка: {e}")

    def _save(self) -> None:
        self.repo.save(self.script)
        display.info(f"Сохранено в {self.repo.path}")

    # -- shared prompts --

    def _prompt_messages(self, state: int | None = None) -> list[Message]:
        prefix = f"Узел {state}: " if state is not None else ""
        messages: list[Message] = []
        while True:
            if not messages:
                label = f"{prefix}Текст сообщения (в редакторе)"
            else:
                label = f"{prefix}Следующее сообщение (в редакторе)"
            text = prompts.editor(label)
            if text:
                messages.append(Message(text=text))
                display.success(f"  Сообщение добавлено ({len(text)} символов).")
            if not messages:
                display.warning("  Требуется хотя бы одно сообщение.")
                continue
            if not prompts.confirm(f"{prefix}Добавить ещё одно сообщение?", default=False):
                break
        return messages

    def _prompt_options(self, state: int | None = None) -> list[str]:
        prefix = f"Узел {state}: " if state is not None else ""
        options: list[str] = []
        while prompts.confirm(f"{prefix}Добавить кнопку?", default=False):
            opt = prompts.text(f"{prefix}Текст кнопки")
            if opt:
                options.append(opt)
        return options

    def _prompt_single_edge(self, source_state: int, index: int) -> Edge | None:
        prefix = f"Узел {source_state}, Ребро #{index}"
        pred_type = prompts.select_predicate_type()
        if pred_type is None:
            return None

        predicate: Predicate
        if pred_type == "always":
            predicate = AlwaysPredicate()
        elif pred_type == "exact":
            txt = prompts.text(f"{prefix} - совпадение с текстом", default="")
            if txt is None:
                return None
            predicate = ExactPredicate(text=txt)
        else:
            pat = prompts.text(f"{prefix} - регулярное выражение", default=".*")
            if pat is None:
                return None
            predicate = RegexPredicate(pattern=pat)

        to_state = prompts.integer(f"{prefix} - конечное состояние", default=source_state + 1)
        if to_state is None:
            return None

        operation = prompts.select_operation()
        if operation is None:
            return None

        return Edge(
            predicate=predicate,
            to=to_state,
            operation=cast(Literal["noop", "save", "append"], operation),
        )

    # -- CRUD: nodes --

    def _add_node(self) -> None:
        next_st = self.script.next_state()
        state = prompts.integer("Состояние", default=next_st)
        if state is None:
            return
        if self.script.has_node(state):
            display.error(f"Узел {state} уже существует.")
            return

        title = prompts.text(f"Узел {state} - заголовок", default=f"Узел {state}")
        if not title:
            title = f"Узел {state}"

        messages = self._prompt_messages(state)
        options = self._prompt_options(state)

        edges: list[Edge] = []
        edge_index = 1
        while prompts.confirm(f"Узел {state}: Добавить исходящее ребро #{edge_index}?", default=False):
            edge = self._prompt_single_edge(state, edge_index)
            if edge:
                edges.append(edge)
                edge_index += 1

        node = Node(
            state=state,
            title=title,
            messages=messages,
            edges=edges,
            options=options,
        )
        self.script.add_node(node)
        self._save()
        display.success(f"Узел {state} добавлен.")

    def _edit_node(self) -> None:
        if not self.script.nodes:
            display.warning("Нет узлов для редактирования.")
            return

        state = prompts.select_node(self.script.nodes, "Выберите узел для редактирования")
        if state is None:
            return

        node = self.script.get_node(state)
        if node is None:
            return

        display.show_node(node)

        field = prompts.select(
            "Редактирование",
            ["Заголовок", "Сообщения", "Кнопки", "Назад"],
        )
        if field is None or field == "Назад":
            return

        if field == "Заголовок":
            new_title = prompts.text("Заголовок", default=node.title)
            if new_title:
                node.title = new_title
        elif field == "Сообщения":
            display.info("Заново введите все сообщения для узла")
            node.messages = self._prompt_messages()
        elif field == "Опции":
            display.info("Заново введите все опции для узла")
            node.options = self._prompt_options()

        self._save()
        display.success(f"Узел {state} обновлён.")

    def _delete_node(self) -> None:
        if not self.script.nodes:
            display.warning("Нет узлов для удаления")
            return

        state = prompts.select_node(self.script.nodes, "Выберите узел для удаления")
        if state is None:
            return

        if not prompts.confirm(
            f"Удалить узел {state}? Будут удалены все входящие рёбра",
            default=False,
        ):
            return

        self.script.remove_node(state)
        self._save()
        display.success(f"Узел {state} удалён")

    # -- CRUD: edges --

    def _add_edge(self) -> None:
        if not self.script.nodes:
            display.warning("Сначала добавьте хотя бы один узел")
            return

        state = prompts.select_node(self.script.nodes, "Выберите исходный узел")
        if state is None:
            return

        node = self.script.get_node(state)
        if node is None:
            return

        edge_index = len(node.edges) + 1
        edge = self._prompt_single_edge(state, edge_index)
        if edge is None:
            return

        node.edges.append(edge)
        self._save()
        display.success(f"Добавлено ребро {state} -> {edge.to}.")

    def _delete_edge(self) -> None:
        nodes_with_edges = [n for n in self.script.nodes if n.edges]
        if not nodes_with_edges:
            display.warning("Нет узлов с ребрами")
            return

        state = prompts.select_node(nodes_with_edges, "Выберите узел")
        if state is None:
            return

        node = self.script.get_node(state)
        if node is None:
            return

        display.show_edges(node)

        choices = [str(i) for i in range(1, len(node.edges) + 1)]
        idx_str = prompts.select("Выберите ребро для удаления", choices)
        if idx_str is None:
            return

        idx = int(idx_str) - 1
        removed = node.edges.pop(idx)
        self._save()
        display.success(f"Ребро #{idx + 1} (-> {removed.to}) удалено.")

    # -- CRUD: entries --

    def _add_entry(self) -> None:
        key = prompts.text("Ключ точки входа")
        if not key:
            return

        for e in self.script.entries:
            if e.key == key:
                display.error(f"Точка входа '{key}' уже существует.")
                return

        if not self.script.nodes:
            display.warning("Нет узлов. Добавьте сначала хотя бы один узел")
            return

        state = prompts.select_node(self.script.nodes, "Выберите начальный узел")
        if state is None:
            return

        self.script.add_entry(Entry(key=key, start=state))
        self._save()
        display.success(f"Точка входа /{key} -> узел {state} создана.")

    def _delete_entry(self) -> None:
        if not self.script.entries:
            display.warning("Нет точек входа для удаления")
            return

        choices = [f"/{e.key} -> state {e.start}" for e in self.script.entries]
        selected = prompts.select("Выберите точку входа для удаления", choices)
        if selected is None:
            return

        idx = choices.index(selected)
        key = self.script.entries[idx].key
        if not prompts.confirm(f"Удалить точку входа /{key}?", default=False):
            return

        self.script.remove_entry(key)
        self._save()
        display.success(f"Точка входа /{key} удалена.")

    # -- display --

    def _show_graph(self) -> None:
        if not self.script.nodes:
            display.warning("Не создано ни одного узла.")
            return
        display.show_graph_spine(self.script)

    def _view_node(self) -> None:
        if not self.script.nodes:
            display.warning("Не создано ни одного узла.")
            return

        state = prompts.select_node(self.script.nodes, "Выберите узел для просмотра")
        if state is None:
            return

        node = self.script.get_node(state)
        if node is None:
            return

        display.show_node(node)
