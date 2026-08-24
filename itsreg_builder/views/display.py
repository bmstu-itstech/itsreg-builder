from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from itsreg_builder.models.graph import GraphIndex, predicate_label
from itsreg_builder.models.script import Node, Script

console = Console()


def info(message: str) -> None:
    console.print(message, style="cyan")


def success(message: str) -> None:
    console.print(message, style="green")


def warning(message: str) -> None:
    console.print(message, style="yellow")


def error(message: str) -> None:
    console.print(message, style="red")


def _truncate(text: str, width: int = 30) -> str:
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def node_label(node: Node, max_title: int = 30) -> str:
    return f"[{node.state}] {_truncate(node.title, max_title)}"


# -- header --


def show_header(script: Script) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold]{script.desc}[/bold]\n"
            f"Узлы: {len(script.nodes)}  |  Точки входа: {len(script.entries)}",
            title="Сценарий",
            border_style="cyan",
        )
    )
    console.print()


# -- node detail --


def show_node(node: Node) -> None:
    lines: list[str] = []
    lines.append(f"[bold cyan][{node.state}] {node.title}[/bold cyan]")
    lines.append("")

    lines.append("[bold]Сообщения:[/bold]")
    for msg in node.messages:
        for line in msg.text.splitlines():
            lines.append(f"  {line}")
    lines.append("")

    if node.options:
        lines.append("[bold]Кнопки:[/bold]  " + ", ".join(f"[{o}]" for o in node.options))
        lines.append("")

    if node.edges:
        lines.append("[bold]Ребра:[/bold]")
        for i, edge in enumerate(node.edges, 1):
            lines.append(f"  #{i}: \\[{predicate_label(edge)}] -> {edge.to}  ({edge.operation})")
    else:
        lines.append("[dim]Нет исходящих ребер[/dim]")

    console.print(Panel("\n".join(lines), border_style="cyan"))


def show_edges(node: Node) -> None:
    if not node.edges:
        warning(f"Узел {node.state} не имеет исходящих ребер.")
        return
    table = Table(title=f"Ребра узла {node.state}")
    table.add_column("#", justify="center", width=4)
    table.add_column("Предикат", min_width=15)
    table.add_column("К узлу", justify="center", width=6)
    table.add_column("Действие", width=10)
    for i, edge in enumerate(node.edges, 1):
        table.add_row(str(i), predicate_label(edge), str(edge.to), edge.operation)
    console.print(table)


# -- graph: spine --


def show_graph_spine(script: Script) -> None:
    idx = GraphIndex(script)
    cyclic = idx.cycle_states()
    unreachable = idx.unreachable_states()

    lines: list[str] = []

    if idx.entry_list:
        lines.append("[bold]Точки входа:[/bold]")
        for key, start in idx.entry_list:
            lines.append(f"  /{key} -> {start}")
        lines.append("")

    reachable = [s for s in idx.order if s not in unreachable]
    lines.extend(_spine_section(idx, reachable, cyclic, ""))

    if unreachable:
        lines.append("")
        lines.append("[bold yellow]Недостижимо:[/bold yellow]")
        orphans = sorted(unreachable)
        lines.extend(_spine_section(idx, orphans, cyclic, "  "))

    console.print("\n".join(lines))


def _spine_section(
    idx: GraphIndex,
    states: list[int],
    cyclic: set[int],
    indent: str,
) -> list[str]:
    lines: list[str] = []
    last = len(states) - 1

    for i, s in enumerate(states):
        node = idx.by_state.get(s)
        if node is None:
            continue

        marker = " [yellow]↺[/yellow]" if s in cyclic else ""
        lines.append(f"{indent}[bold]\\[{s}][/bold] {node.title}{marker}")

        nxt = states[i + 1] if i < last else None
        forwards = idx.forward_edges(s)

        spine_edges = [e for e in forwards if e.to == nxt]
        if len(spine_edges) == 1:
            e = spine_edges[0]
            lines.append(f"{indent}  │ [magenta]\\[{predicate_label(e)}][/magenta]")

        for e in forwards:
            if e.to == nxt and len(spine_edges) == 1:
                continue
            lines.append(f"{indent}  └─[magenta]\\[{predicate_label(e)}][/magenta]→ {e.to}")

        if i < last:
            lines.append(f"{indent}  │")

    return lines


# -- graph: tree subgraph from a given state --


def show_graph_tree(script: Script, root: int, depth: int = 3) -> None:
    idx = GraphIndex(script)
    node = idx.by_state.get(root)
    if node is None:
        error(f"Узел {root} не найден.")
        return

    cyclic = idx.cycle_states()
    lines: list[str] = []
    visited: set[int] = set()
    _walk_tree(idx, root, "", None, visited, lines, cyclic, depth, 0)

    console.print("\n".join(lines))


def _walk_tree(
    idx: GraphIndex,
    state: int,
    prefix: str,
    incoming: str | None,
    visited: set[int],
    lines: list[str],
    cyclic: set[int],
    max_depth: int,
    depth: int,
) -> None:
    node = idx.by_state.get(state)
    if node is None:
        return

    cycle_mark = " [yellow]↺[/yellow]" if state in cyclic else ""

    if incoming is not None:
        lines.append(
            f"{prefix}── [magenta]\\[{incoming}][/magenta]→ "
            f"[bold]{state}[/bold] · {node.title}{cycle_mark}"
        )
    else:
        lines.append(f"[bold cyan]{state}[/bold cyan] · {node.title}{cycle_mark}")

    if state in visited:
        return
    visited.add(state)

    if depth >= max_depth:
        if node.edges:
            lines.append(f"{prefix}   [dim]... ({len(node.edges)} ребер)[/dim]")
        return

    edges = node.edges
    last_idx = len(edges) - 1
    for i, e in enumerate(edges):
        is_last = i == last_idx
        branch = "└──" if is_last else "├──"

        if e.to in visited:
            pred = predicate_label(e)
            lines.append(
                f"{prefix}   {branch} [magenta]\\[{pred}][/magenta]→ {e.to} [yellow]↺[/yellow]"
            )
        else:
            child_prefix = prefix + ("   " if is_last else "│  ")
            _walk_tree(
                idx,
                e.to,
                child_prefix,
                predicate_label(e),
                visited,
                lines,
                cyclic,
                max_depth,
                depth + 1,
            )
