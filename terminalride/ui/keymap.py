"""Central keymap definitions for keys and hints.

This module provides a single source of truth for keyboard hints used by
the legend panel, help overlay, and status bar. It does not dispatch actions;
views continue to handle keys. This avoids drift between displayed hints and
what keys actually do.
"""

from typing import Dict, List, Tuple


Hint = Tuple[str, str, bool]  # (key, label, enabled)


def get_hints(current_view: str, connected: bool) -> Dict[str, List[Hint]]:
    """Return grouped key hints for the given view and connection state.

    Args:
        current_view: Lowercase view name (e.g., 'home', 'live_erg')
        connected: Whether trainer is connected

    Returns:
        Dict with groups: 'global' and 'view', each a list of (key, label, enabled)
    """
    global_hints: List[Hint] = [
        ("l", "Legend", True),
        ("?", "Help", True),
        ("Esc", "Back", True),
    ]
    if current_view == "home":
        global_hints.append(("q", "Quit", True))
    elif current_view.startswith("live_"):
        global_hints.insert(0, ("Space", "Pause", True))

    view_hints: List[Hint] = []

    if current_view == "home":
        view_hints.extend(
            [
                ("1", "Free", connected),
                ("2", "ERG", connected),
                ("3", "SIM", connected),
                ("d", "Devices", True),
                ("s", "Stats", True),
                ("c", "Settings", True),
            ]
        )
    elif current_view == "connect":
        view_hints.extend(
            [
                ("r", "Retry", True),
                ("Any", "Continue when connected", connected),
            ]
        )
    elif current_view == "devices":
        view_hints.extend(
            [
                ("r", "Rescan", True),
                ("c", "Trainer", True),
                ("h", "Heart Rate", True),
            ]
        )
    elif current_view == "live_erg":
        view_hints.extend(
            [
                ("+/-", "Target", True),
                ("L", "Lap", True),
                ("s", "Save", True),
            ]
        )
    elif current_view == "live_sim":
        view_hints.extend(
            [
                ("↑/↓", "Grade", True),
                ("L", "Lap", True),
                ("s", "Save", True),
            ]
        )
    elif current_view == "live_free":
        view_hints.extend(
            [
                ("L", "Lap", True),
                ("s", "Save", True),
            ]
        )
    elif current_view == "stats":
        view_hints.extend(
            [
                ("e", "Export", True),
                ("a", "Export all", True),
                ("d", "Delete", True),
            ]
        )
    elif current_view == "settings":
        view_hints.extend([])

    return {"global": global_hints, "view": view_hints}


def condensed_line(current_view: str, connected: bool, max_items: int = 6) -> str:
    """Return a compact status-line hint string like '1 Free  2 ERG  l Legend  ? Help'."""
    hints = get_hints(current_view, connected)

    items: List[str] = []
    for key, label, enabled in hints["view"] + hints["global"]:
        if len(items) >= max_items:
            break
        if enabled:
            items.append(f"{key} {label}")
    return "  ".join(items)

