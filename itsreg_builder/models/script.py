from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    text: str


class AlwaysPredicate(BaseModel):
    type: Literal["always"] = "always"


class ExactPredicate(BaseModel):
    type: Literal["exact"] = "exact"
    text: str


class RegexPredicate(BaseModel):
    type: Literal["regex"] = "regex"
    pattern: str


Predicate = Annotated[
    AlwaysPredicate | ExactPredicate | RegexPredicate,
    Field(discriminator="type"),
]


class Edge(BaseModel):
    predicate: Predicate
    to: int
    operation: Literal["noop", "save", "append"]


class Node(BaseModel):
    state: int
    title: str
    messages: list[Message]
    edges: list[Edge] = []
    options: list[str] = []


class Entry(BaseModel):
    key: str
    start: int


class Script(BaseModel):
    desc: str
    nodes: list[Node] = []
    entries: list[Entry] = []

    def get_node(self, state: int) -> Node | None:
        for node in self.nodes:
            if node.state == state:
                return node
        return None

    def has_node(self, state: int) -> bool:
        return self.get_node(state) is not None

    def next_state(self) -> int:
        if not self.nodes:
            return 1
        return max(n.state for n in self.nodes) + 1

    def add_node(self, node: Node) -> None:
        if self.has_node(node.state):
            raise ValueError(f"Node with state {node.state} already exists")
        self.nodes.append(node)

    def remove_node(self, state: int) -> None:
        self.nodes = [n for n in self.nodes if n.state != state]
        for node in self.nodes:
            node.edges = [e for e in node.edges if e.to != state]
        self.entries = [e for e in self.entries if e.start != state]

    def add_entry(self, entry: Entry) -> None:
        for existing in self.entries:
            if existing.key == entry.key:
                raise ValueError(f"Entry with key '{entry.key}' already exists")
        self.entries.append(entry)

    def remove_entry(self, key: str) -> None:
        self.entries = [e for e in self.entries if e.key != key]
