from __future__ import annotations

from collections import deque

from itsreg_builder.models.script import (
    AlwaysPredicate,
    Edge,
    ExactPredicate,
    RegexPredicate,
    Script,
)


def predicate_label(edge: Edge) -> str:
    p = edge.predicate
    if isinstance(p, AlwaysPredicate):
        return "always"
    if isinstance(p, ExactPredicate):
        return f'"{p.text}"'
    if isinstance(p, RegexPredicate):
        return f"/{p.pattern}/"
    return "?"


class GraphIndex:
    def __init__(self, script: Script) -> None:
        self.by_state = {n.state: n for n in script.nodes}

        entry_list = sorted(
            ((e.key, e.start) for e in script.entries if e.start in self.by_state),
            key=lambda x: x[0],
        )
        seen_keys: set[str] = set()
        self.entry_list: list[tuple[str, int]] = []
        for k, s in entry_list:
            if k not in seen_keys:
                seen_keys.add(k)
                self.entry_list.append((k, s))

        roots = sorted(set(s for _, s in self.entry_list))

        seen: set[int] = set(roots)
        order: list[int] = list(roots)
        queue: deque[int] = deque(roots)
        while queue:
            s = queue.popleft()
            node = self.by_state.get(s)
            if node is None:
                continue
            for edge in node.edges:
                if edge.to not in seen:
                    seen.add(edge.to)
                    order.append(edge.to)
                    queue.append(edge.to)

        unreachable = sorted(s for s in self.by_state if s not in seen)
        order.extend(unreachable)

        self.order = order
        self._pos = {s: i for i, s in enumerate(order)}
        self._unreachable: set[int] = set(unreachable)

    def entries(self) -> list[int]:
        return sorted(set(s for _, s in self.entry_list))

    def forward_edges(self, state: int) -> list[Edge]:
        node = self.by_state.get(state)
        if node is None:
            return []
        from_pos = self._pos.get(state)
        result = []
        for e in node.edges:
            if e.to == state:
                continue
            to_pos = self._pos.get(e.to)
            if from_pos is not None and to_pos is not None and to_pos < from_pos:
                continue
            result.append(e)
        return result

    def back_edges(self, state: int) -> list[Edge]:
        node = self.by_state.get(state)
        if node is None:
            return []
        from_pos = self._pos.get(state)
        result = []
        for e in node.edges:
            if e.to == state:
                result.append(e)
                continue
            to_pos = self._pos.get(e.to)
            if from_pos is not None and to_pos is not None and to_pos < from_pos:
                result.append(e)
        return result

    def cycle_states(self) -> set[int]:
        cyclic: set[int] = set()
        color: dict[int, int] = {}
        stack: list[int] = []

        for root in self.order:
            if color.get(root, 0) == 0:
                self._dfs_cycles(root, color, stack, cyclic)
        return cyclic

    def _dfs_cycles(
        self,
        state: int,
        color: dict[int, int],
        stack: list[int],
        cyclic: set[int],
    ) -> None:
        color[state] = 1
        stack.append(state)

        node = self.by_state.get(state)
        if node:
            for edge in node.edges:
                c = color.get(edge.to, 0)
                if c == 1:
                    try:
                        start = stack.index(edge.to)
                    except ValueError:
                        pass
                    else:
                        cyclic.update(stack[start:])
                elif c == 0:
                    self._dfs_cycles(edge.to, color, stack, cyclic)

        stack.pop()
        color[state] = 2

    def unreachable_states(self) -> set[int]:
        return set(self._unreachable)
