from __future__ import annotations

from itsreg_builder.models.repository import ScriptRepository
from itsreg_builder.models.script import (
    AlwaysPredicate,
    Edge,
    Entry,
    ExactPredicate,
    Message,
    Node,
    RegexPredicate,
    Script,
)
from itsreg_builder.views import display, prompts


class ScriptController:
    def __init__(self, repository: ScriptRepository):
        self.repo = repository
        self.script: Script | None = None

    def run(self) -> None:
        self.script = self.repo.load()

        if self.script is None:
            display.info("No script found. Starting creation wizard...\n")
            self.script = self._wizard_create()
            self._save()
            display.success("Script created and saved!")
        else:
            display.success(f"Loaded script from {self.repo.path}")

        display.show_summary(self.script)
        self._main_loop()

    # -- main loop --

    def _main_loop(self) -> None:
        handlers = {
            "Add node": self._add_node,
            "Edit node": self._edit_node,
            "Delete node": self._delete_node,
            "Add edge": self._add_edge,
            "Delete edge": self._delete_edge,
            "Add entry": self._add_entry,
            "Delete entry": self._delete_entry,
            "Show script": self._show_script,
            "Show JSON": self._show_json,
            "Creation wizard": self._run_wizard,
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

    # -- wizard --

    def _wizard_create(self) -> Script:
        desc = prompts.text("Script description", default="My script")
        if not desc:
            desc = "My script"

        start_state = prompts.integer("Start state number", default=1) or 1

        nodes_by_state: dict[int, Node] = {}
        in_progress: set[int] = set()
        self._build_node_recursive(nodes_by_state, start_state, in_progress)

        entries = self._prompt_entries_batch(nodes_by_state, start_state)

        return Script(
            desc=desc,
            nodes=list(nodes_by_state.values()),
            entries=entries,
        )

    def _build_node_recursive(
        self,
        nodes_by_state: dict[int, Node],
        state: int,
        in_progress: set[int],
    ) -> None:
        if state in nodes_by_state:
            display.info(f"Node {state} already exists, skipping.")
            return
        if state in in_progress:
            display.info(f"Node {state} is being built (cycle detected), skipping.")
            return

        in_progress.add(state)
        display.info(f"\n--- Building node {state} ---")

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
                to_state = edge.to
                if to_state not in nodes_by_state and to_state not in in_progress:
                    self._build_node_recursive(nodes_by_state, to_state, in_progress)
                elif to_state in nodes_by_state:
                    display.info(f"  -> Node {to_state} already exists.")
                else:
                    display.info(f"  -> Cycle to node {to_state}.")
                edge_index += 1

        node = Node(
            state=state,
            title=title,
            messages=messages,
            edges=edges,
            options=options,
        )
        nodes_by_state[state] = node
        in_progress.discard(state)

    def _prompt_messages(self, state: int | None = None) -> list[Message]:
        prefix = f"Node {state}: " if state is not None else ""
        messages: list[Message] = []
        while True:
            label = f"{prefix}Message text (opens editor)" if not messages else f"{prefix}Next message (opens editor)"
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

        return Edge(predicate=predicate, to=to_state, operation=operation)

    def _prompt_entries_batch(
        self, nodes_by_state: dict[int, Node], default_start: int
    ) -> list[Entry]:
        entries: list[Entry] = []
        states = set(nodes_by_state.keys())

        while True:
            default_key = "start" if not entries else ""
            key = prompts.text("Entry key (e.g. 'start')", default=default_key)
            if not key:
                break

            start = prompts.integer("Entry start state", default=default_start)
            if start is None:
                break
            if start not in states:
                display.warning(
                    f"State {start} does not exist. "
                    f"Available: {sorted(states)}"
                )
                continue

            entries.append(Entry(key=key, start=start))
            if not prompts.confirm("Add another entry?", default=False):
                break

        if not entries:
            entries.append(Entry(key="start", start=default_start))
            display.info("  Default entry added: /start -> state " + str(default_start))

        return entries

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

        messages = self._prompt_messages()
        options = self._prompt_options()

        node = Node(state=state, title=title, messages=messages, options=options)
        self.script.add_node(node)
        self._save()
        display.success(f"Node {state} added.")

    def _edit_node(self) -> None:
        states = [n.state for n in self.script.nodes]
        if not states:
            display.warning("No nodes to edit.")
            return

        state = prompts.select_node(states, "Select node to edit")
        if state is None:
            return

        node = self.script.get_node(state)
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
        states = [n.state for n in self.script.nodes]
        if not states:
            display.warning("No nodes to delete.")
            return

        state = prompts.select_node(states, "Select node to delete")
        if state is None:
            return

        if not prompts.confirm(
            f"Delete node {state}? This also removes edges pointing to it.",
            default=False,
        ):
            return

        self.script.remove_node(state)
        self._save()
        display.success(f"Node {state} deleted.")

    # -- CRUD: edges --

    def _add_edge(self) -> None:
        states = [n.state for n in self.script.nodes]
        if not states:
            display.warning("No nodes. Add a node first.")
            return

        state = prompts.select_node(states, "Add edge to which node?")
        if state is None:
            return

        node = self.script.get_node(state)
        edge_index = len(node.edges) + 1
        edge = self._prompt_single_edge(state, edge_index)
        if edge is None:
            return

        node.edges.append(edge)
        self._save()
        display.success(f"Edge added to node {state} -> {edge.to}.")

    def _delete_edge(self) -> None:
        states = [n.state for n in self.script.nodes if n.edges]
        if not states:
            display.warning("No nodes with edges.")
            return

        state = prompts.select_node(states, "Delete edge from which node?")
        if state is None:
            return

        node = self.script.get_node(state)
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

        states = [n.state for n in self.script.nodes]
        if not states:
            display.warning("No nodes. Add a node first.")
            return

        state = prompts.select_node(states, "Entry start state")
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

    def _show_script(self) -> None:
        display.show_summary(self.script)

    def _show_json(self) -> None:
        display.show_json(self.script)

    # -- wizard on existing script --

    def _run_wizard(self) -> None:
        next_st = self.script.next_state()
        start = prompts.integer("Start building from state", default=next_st)
        if start is None:
            return

        if self.script.has_node(start):
            display.warning(f"Node {start} already exists. Pick a new state number.")
            return

        existing = {n.state: n for n in self.script.nodes}
        in_progress: set[int] = set(existing.keys())
        nodes_by_state: dict[int, Node] = dict(existing)

        self._build_node_recursive(nodes_by_state, start, in_progress)

        new_nodes = [n for s, n in nodes_by_state.items() if s not in existing]
        for node in new_nodes:
            self.script.nodes.append(node)

        if new_nodes:
            self._save()
            display.success(f"{len(new_nodes)} new node(s) added.")
        else:
            display.info("No new nodes created.")
