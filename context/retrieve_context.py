#!/usr/bin/env python3
"""
Context Retrieval Utility for ClassSnap.
Automatically reads the context directory and reports the current system state,
completed phases, test status, and architecture guidelines.
"""

import json
from pathlib import Path
from typing import Any, Dict


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def get_context_dir() -> Path:
    return get_base_dir() / "context"


def load_system_state() -> Dict[str, Any]:
    state_file = get_context_dir() / "system_state.json"
    if not state_file.exists():
        return {"error": "System state file not found"}
    with open(state_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_phase_context(phase_number: int) -> str:
    phase_file = get_context_dir() / f"phase_{phase_number}_context.md"
    if not phase_file.exists():
        return f"No context file found for phase {phase_number}"
    return phase_file.read_text(encoding="utf-8")


def get_full_context_summary() -> str:
    state = load_system_state()
    lines = [
        "=" * 60,
        f"ClassSnap Context Summary — Current Phase: {state.get('current_phase')}",
        f"Last Updated: {state.get('last_updated')}",
        "=" * 60,
        "\nPhase Statuses:",
    ]
    phases = state.get("phases", {})
    for phase_key, info in phases.items():
        status = info.get("status", "UNKNOWN")
        name = info.get("name", phase_key)
        lines.append(f"  - [{status}] {phase_key.upper()}: {name}")

    lines.append("\nKey Architectural Principles:")
    for rule in state.get("key_architectural_decisions", []):
        lines.append(f"  * {rule}")

    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_full_context_summary())
