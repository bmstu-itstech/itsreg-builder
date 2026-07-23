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
            display.info("No script found. Creating a new one.\n")
            desc = prompts.text("Script description", default="My script")
            if not desc:
                desc = "My script"
            self.script = Script(desc=desc)
            self._save()
            display.success("Script created!")
        else:
            self.script = loaded
            display.success(f"Loaded script from {self.repo.path}")

        display.show_header(self.script)
        self._main_loop()

    # -- main loop --

    def _main_loop(self) -> None:
        handlers: dict[str, Callable[[], None]] = {
            "Add node": self._add_node,
            "Edit node": self._edit_node,
            "Delete node": self._delete_node,
            "Add edge": self._add_edge,
            "Delete edge": self._delete_edge,
            "Add entry": self._add_entry,
            "Delete entry": self._delete_entry,
            "Show graph": self._show_graph,
            "View node": self._view_node,
        }

        while True:
            action = prompts.select_main_action()
            if action is None or action == "Exit":
                display.info("Goodbye!")
                break
            handler = handlers.get(action)
            if handler:
                try:
                    handler()
                except Exception as e:
                    display.error(f"Error: {e}")

    def _save(self) -> None:
        self.repo.save(self.script)
        display.info(f"Saved to {self.repo.path}")

    # -- shared prompts --

    def _prompt_messages(self, state: int | None = None) -> list[Message]:
        prefix = f"Node {state}: " if state is not None else ""
        messages: list[Message] = []
        while True:
            if not messages:
                label = f"{prefix}Message text (opens editor)"
            else:
                label = f"{prefix}Next message (opens editor)"
            text = prompts.editor(label)
            if text:
                messages.append(Message(text=text))
                display.success(f"  Message added ({len(text)} chars).")
            if not messages:
                display.warning("  At least one message is required.")
                continue
            if not prompts.confirm(f"{prefix}Add another message?", default=False):
                break
        return messages

    def _prompt_options(self, state: int | None = None) -> list[str]:
        prefix = f"Node {state}: " if state is not None else ""
        options: list[str] = []
        while prompts.confirm(f"{prefix}Add a button option?", default=False):
            opt = prompts.text(f"{prefix}Button text")
            if opt:
                options.append(opt)
        return options

    def _prompt_single_edge(self, source_state: int, index: int) -> Edge | None:
        prefix = f"Node {source_state}, Edge #{index}"
        pred_type = prompts.select_predicate_type()
        if pred_type is None:
            return None

        predicate: Predicate
        if pred_type == "always":
            predicate = AlwaysPredicate()
        elif pred_type == "exact":
            txt = prompts.text(f"{prefix} - Expected text", default="")
            if txt is None:
                return None
            predicate = ExactPredicate(text=txt)
        else:
            pat = prompts.text(f"{prefix} - Regex pattern", default=".*")
            if pat is None:
                return None
            predicate = RegexPredicate(pattern=pat)

        to_state = prompts.integer(f"{prefix} - Target state", default=source_state + 1)
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
        state = prompts.integer("State number", default=next_st)
        if state is None:
            return
        if self.script.has_node(state):
            display.error(f"Node {state} already exists.")
            return

        title = prompts.text(f"Node {state} - Title", default=f"state-{state}")
        if not title:
            title = f"state-{state}"

        messages = self._prompt_messages(state)
        options = self._prompt_options(state)

        edges: list[Edge] = []
        edge_index = 1
        while prompts.confirm(f"Node {state}: Add outgoing edge #{edge_index}?", default=False):
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
        display.success(f"Node {state} added.")

    def _edit_node(self) -> None:
        if not self.script.nodes:
            display.warning("No nodes to edit.")
            return

        state = prompts.select_node(self.script.nodes, "Select node to edit")
        if state is None:
            return

        node = self.script.get_node(state)
        if node is None:
            return

        display.show_node(node)

        field = prompts.select(
            "What to edit?",
            ["Title", "Messages", "Options", "Back"],
        )
        if field is None or field == "Back":
            return

        if field == "Title":
            new_title = prompts.text("New title", default=node.title)
            if new_title:
                node.title = new_title
        elif field == "Messages":
            display.info("Re-enter all messages for this node.")
            node.messages = self._prompt_messages()
        elif field == "Options":
            display.info("Re-enter all options for this node.")
            node.options = self._prompt_options()

        self._save()
        display.success(f"Node {state} updated.")

    def _delete_node(self) -> None:
        if not self.script.nodes:
            display.warning("No nodes to delete.")
            return

        state = prompts.select_node(self.script.nodes, "Select node to delete")
        if state is None:
            return

        if not prompts.confirm(
            f"Delete node {state}? Edges pointing to it will be removed.",
            default=False,
        ):
            return

        self.script.remove_node(state)
        self._save()
        display.success(f"Node {state} deleted.")

    # -- CRUD: edges --

    def _add_edge(self) -> None:
        if not self.script.nodes:
            display.warning("No nodes. Add a node first.")
            return

        state = prompts.select_node(self.script.nodes, "Add edge to which node?")
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
        display.success(f"Edge added to node {state} -> {edge.to}.")

    def _delete_edge(self) -> None:
        nodes_with_edges = [n for n in self.script.nodes if n.edges]
        if not nodes_with_edges:
            display.warning("No nodes with edges.")
            return

        state = prompts.select_node(nodes_with_edges, "Delete edge from which node?")
        if state is None:
            return

        node = self.script.get_node(state)
        if node is None:
            return

        display.show_edges(node)

        choices = [str(i) for i in range(1, len(node.edges) + 1)]
        idx_str = prompts.select("Edge number to delete", choices)
        if idx_str is None:
            return

        idx = int(idx_str) - 1
        removed = node.edges.pop(idx)
        self._save()
        display.success(f"Edge #{idx + 1} (-> {removed.to}) deleted.")

    # -- CRUD: entries --

    def _add_entry(self) -> None:
        key = prompts.text("Entry key")
        if not key:
            return

        for e in self.script.entries:
            if e.key == key:
                display.error(f"Entry '{key}' already exists.")
                return

        if not self.script.nodes:
            display.warning("No nodes. Add a node first.")
            return

        state = prompts.select_node(self.script.nodes, "Entry start state")
        if state is None:
            return

        self.script.add_entry(Entry(key=key, start=state))
        self._save()
        display.success(f"Entry /{key} -> state {state} added.")

    def _delete_entry(self) -> None:
        if not self.script.entries:
            display.warning("No entries to delete.")
            return

        choices = [f"/{e.key} -> state {e.start}" for e in self.script.entries]
        selected = prompts.select("Select entry to delete", choices)
        if selected is None:
            return

        idx = choices.index(selected)
        key = self.script.entries[idx].key
        if not prompts.confirm(f"Delete entry /{key}?", default=False):
            return

        self.script.remove_entry(key)
        self._save()
        display.success(f"Entry /{key} deleted.")

    # -- display --

    def _show_graph(self) -> None:
        if not self.script.nodes:
            display.warning("No nodes yet.")
            return

        mode = prompts.select("Graph view", ["Full (spine)", "From node (tree)"])
        if mode is None:
            return

        if mode == "Full (spine)":
            display.show_graph_spine(self.script)
        else:
            state = prompts.select_node(self.script.nodes, "Root node for subgraph")
            if state is None:
                return
            depth = prompts.integer("Tree depth", default=3)
            if depth is None:
                depth = 3
            display.show_graph_tree(self.script, state, depth)

    def _view_node(self) -> None:
        if not self.script.nodes:
            display.warning("No nodes yet.")
            return

        state = prompts.select_node(self.script.nodes, "Select node to view")
        if state is None:
            return

        node = self.script.get_node(state)
        if node is None:
            return

        display.show_node(node)
