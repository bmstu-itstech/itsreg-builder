from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from itsreg_builder.models.script import (
    AlwaysPredicate,
    Edge,
    ExactPredicate,
    Node,
    RegexPredicate,
    Script,
)

console = Console()


def info(message: str) -> None:
    console.print(message, style="cyan")


def success(message: str) -> None:
    console.print(message, style="green")


def warning(message: str) -> None:
    console.print(message, style="yellow")


def error(message: str) -> None:
    console.print(message, style="red")


def _format_predicate(edge: Edge) -> str:
    p = edge.predicate
    if isinstance(p, AlwaysPredicate):
        return "always"
    if isinstance(p, ExactPredicate):
        return f'exact("{p.text}")'
    if isinstance(p, RegexPredicate):
        return f"regex(/{p.pattern}/)"
    return "?"


def show_summary(script: Script) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold]{script.desc}[/bold]\n"
            f"Nodes: {len(script.nodes)}  |  Entries: {len(script.entries)}",
            title="Script",
            border_style="cyan",
        )
    )

    if script.nodes:
        table = Table(title="Nodes", show_lines=True)
        table.add_column("State", style="bold", justify="center", width=6)
        table.add_column("Title", min_width=12)
        table.add_column("Messages", min_width=20)
        table.add_column("Options", min_width=10)
        table.add_column("Edges", min_width=20)

        for node in sorted(script.nodes, key=lambda n: n.state):
            msgs = "\n".join(
                m.text[:60] + ("..." if len(m.text) > 60 else "")
                for m in node.messages
            )
            opts = ", ".join(node.options) if node.options else "-"
            edges = "\n".join(
                f"{_format_predicate(e)} -> {e.to} [{e.operation}]"
                for e in node.edges
            ) or "-"
            table.add_row(str(node.state), node.title, msgs, opts, edges)

        console.print(table)

    if script.entries:
        entry_str = "  ".join(
            f"/{e.key} -> state {e.start}" for e in script.entries
        )
        console.print(f"\n[bold]Entries:[/bold] {entry_str}")

    console.print()


def show_json(script: Script) -> None:
    data = script.model_dump(mode="json")
    console.print_json(json.dumps(data, ensure_ascii=False))


def show_node(node: Node) -> None:
    tree = Tree(f"[bold]Node {node.state}[/bold] - {node.title}")

    msgs_branch = tree.add("[cyan]Messages[/cyan]")
    for msg in node.messages:
        msgs_branch.add(msg.text[:80] + ("..." if len(msg.text) > 80 else ""))

    if node.options:
        opts_branch = tree.add("[cyan]Options[/cyan]")
        for opt in node.options:
            opts_branch.add(opt)

    if node.edges:
        edges_branch = tree.add("[cyan]Edges[/cyan]")
        for i, edge in enumerate(node.edges, 1):
            edges_branch.add(
                f"#{i}: {_format_predicate(edge)} -> state {edge.to} [{edge.operation}]"
            )

    console.print(tree)


def show_edges(node: Node) -> None:
    if not node.edges:
        warning(f"Node {node.state} has no edges.")
        return
    table = Table(title=f"Edges of node {node.state}")
    table.add_column("#", justify="center", width=4)
    table.add_column("Predicate", min_width=15)
    table.add_column("To", justify="center", width=6)
    table.add_column("Operation", width=10)
    for i, edge in enumerate(node.edges, 1):
        table.add_row(str(i), _format_predicate(edge), str(edge.to), edge.operation)
    console.print(table)
