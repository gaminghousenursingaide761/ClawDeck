#!/usr/bin/env python3
"""
Install Claude Code hooks for clawdeck.

Merges hook entries into ~/.claude/settings.json without clobbering
existing hooks from other sources. Uses the "_source": "clawdeck"
tag to identify and replace our entries on re-runs.

Called by setup.sh after the venv is ready.
"""

import json
import os
import shutil
import sys

SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
SOURCE_TAG = "clawdeck"


def build_hooks(deck_hook_path):
    """Build the hook config with the actual install path."""
    cmd = lambda state: f"{deck_hook_path} {state}"
    tag = {"_source": SOURCE_TAG}

    return {
        "Notification": [
            {"matcher": "idle_prompt", "hooks": [{"type": "command", "command": cmd("idle"), **tag}]},
            {"matcher": "permission_prompt", "hooks": [{"type": "command", "command": cmd("permission"), **tag}]},
            {"matcher": "elicitation_dialog", "hooks": [{"type": "command", "command": cmd("idle"), **tag}]},
        ],
        "PreToolUse": [
            {"hooks": [{"type": "command", "command": cmd("pending"), **tag}]},
        ],
        "PostToolUse": [
            {"hooks": [{"type": "command", "command": cmd("working"), **tag}]},
        ],
        "UserPromptSubmit": [
            {"hooks": [{"type": "command", "command": cmd("working"), **tag}]},
        ],
        "Stop": [
            {"hooks": [{"type": "command", "command": cmd("idle"), **tag}]},
        ],
    }


def is_our_entry(entry):
    """Check if a hook entry belongs to clawdeck."""
    if not isinstance(entry, dict):
        return False
    for hook in entry.get("hooks") or []:
        if isinstance(hook, dict) and hook.get("_source") == SOURCE_TAG:
            return True
    return False


def merge_hooks(existing_hooks, new_hooks):
    """Merge new hooks into existing hooks, replacing our old entries."""
    merged = {}
    for event in set(list(existing_hooks.keys()) + list(new_hooks.keys())):
        # Start with existing entries that aren't ours
        kept = [e for e in existing_hooks.get(event, []) if not is_our_entry(e)]
        # Add our new entries
        kept.extend(new_hooks.get(event, []))
        merged[event] = kept
    return merged


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    deck_hook_path = os.path.join(script_dir, "deck-hook.sh")

    new_hooks = build_hooks(deck_hook_path)

    # Load existing settings
    settings = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"  Warning: Could not parse {SETTINGS_PATH}")
            print(f"  A backup will be created before any changes.")
            settings = {}

    existing_hooks = settings.get("hooks", {})
    merged = merge_hooks(existing_hooks, new_hooks)

    # Show what will change
    print()
    print("  The following hooks will be added to ~/.claude/settings.json:")
    print()
    for event, entries in new_hooks.items():
        for entry in entries:
            matcher = entry.get("matcher", "(all)")
            state = entry["hooks"][0]["command"].split()[-1]
            print(f"    {event} [{matcher}] → {state}")
    print()
    print(f"  Hook script: {deck_hook_path}")

    if existing_hooks:
        other_count = sum(1 for event in existing_hooks
                         for e in existing_hooks[event]
                         if not is_our_entry(e))
        if other_count:
            print(f"  ({other_count} existing hook(s) from other sources will be preserved)")
    print()

    # Ask for approval
    answer = input("  Install hooks? [Y/n] ").strip().lower()
    if answer and answer not in ("y", "yes"):
        print("  Skipped hook installation.")
        print(f"  You can install manually — see claude-hooks.json for reference.")
        return

    # Backup existing settings
    if os.path.exists(SETTINGS_PATH):
        backup = SETTINGS_PATH + ".backup"
        shutil.copy2(SETTINGS_PATH, backup)
        print(f"  Backup saved: {backup}")

    # Write merged settings
    settings["hooks"] = merged
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")

    print("  Hooks installed!")
    print()
    print("  NOTE: Restart any running Claude Code sessions to pick up the new hooks.")


if __name__ == "__main__":
    main()
