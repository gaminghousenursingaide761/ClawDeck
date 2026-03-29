"""Tests for multi-device Stream Deck support.

Uses the `multi_controller` fixture which parametrizes across all
supported grid sizes: 5x3, 3x2, 8x4, 4x2.
"""
import pytest
from main import LAYOUTS, NAV_KEYMAPS, NAV_STYLES, DEVICE_PROFILES


# --- Grid dimensions ---

def test_grid_key_in_profiles(multi_controller):
    assert multi_controller.grid_key in DEVICE_PROFILES


def test_enter_key_is_last(multi_controller):
    assert multi_controller.enter_key_index == multi_controller.total_keys - 1


def test_terminal_slots_is_total_minus_one(multi_controller):
    assert multi_controller.deck_terminal_slots == multi_controller.total_keys - 1


def test_total_keys_matches_grid(multi_controller):
    assert multi_controller.total_keys == multi_controller.cols * multi_controller.rows


# --- Layouts per device ---

def test_default_layout_exists(multi_controller):
    grid_layouts = LAYOUTS[multi_controller.grid_key]
    assert "default" in grid_layouts


def test_all_layouts_correct_length(multi_controller):
    grid_layouts = LAYOUTS[multi_controller.grid_key]
    expected = multi_controller.total_keys
    for name, layout in grid_layouts.items():
        assert len(layout) == expected, f"{name}: {len(layout)} != {expected}"


def test_all_layouts_end_with_enter(multi_controller):
    grid_layouts = LAYOUTS[multi_controller.grid_key]
    for name, layout in grid_layouts.items():
        assert layout[-1] == "ENTER", f"{name} ends with '{layout[-1]}'"


def test_default_terminal_count(multi_controller):
    """Default layout should have total_keys - 1 unique terminals."""
    multi_controller.config["layout"] = "default"
    names = multi_controller._get_terminal_names()
    assert len(names) == multi_controller.deck_terminal_slots


def test_get_terminal_names_excludes_enter(multi_controller):
    multi_controller.config["layout"] = "default"
    names = multi_controller._get_terminal_names()
    assert "ENTER" not in names


def test_terminal_slots_cover_all_non_enter_keys(multi_controller):
    multi_controller.config["layout"] = "default"
    slots = multi_controller._get_terminal_slots()
    all_keys = set()
    for key_list in slots.values():
        all_keys.update(key_list)
    expected = set(range(multi_controller.total_keys)) - {multi_controller.enter_key_index}
    assert all_keys == expected


# --- Grid geometry per device ---

def test_grid_rect_top_left_corner(multi_controller):
    screen = multi_controller.screen
    rect = multi_controller._grid_rect(0)
    assert rect["x"] == screen["x"]
    assert rect["y"] == screen["y"]


def test_grid_rect_bottom_right_corner(multi_controller):
    screen = multi_controller.screen
    rect = multi_controller._grid_rect(multi_controller.enter_key_index)
    # Allow ±1 for int truncation rounding in grid calculations
    assert abs((rect["x"] + rect["w"]) - (screen["x"] + screen["w"])) <= 1
    assert abs((rect["y"] + rect["h"]) - (screen["y"] + screen["h"])) <= 1


def test_grid_rect_cell_size(multi_controller):
    screen = multi_controller.screen
    expected_w = screen["w"] / multi_controller.cols
    expected_h = screen["h"] / multi_controller.rows
    for key in range(multi_controller.total_keys):
        rect = multi_controller._grid_rect(key)
        assert abs(rect["w"] - expected_w) < 1
        assert abs(rect["h"] - expected_h) < 1


# --- Nav keymaps per device ---

def test_nav_keymap_exists(multi_controller):
    assert multi_controller.grid_key in NAV_KEYMAPS


def test_nav_styles_exists(multi_controller):
    assert multi_controller.grid_key in NAV_STYLES


def test_nav_keymap_has_enter(multi_controller):
    keymap = NAV_KEYMAPS[multi_controller.grid_key]
    enter_actions = [k for k, v in keymap.items() if v[0] == "enter"]
    assert len(enter_actions) == 1


def test_nav_keymap_has_back(multi_controller):
    keymap = NAV_KEYMAPS[multi_controller.grid_key]
    back_actions = [k for k, v in keymap.items() if v[0] == "back"]
    assert len(back_actions) == 1


def test_nav_keymap_has_number_keys(multi_controller):
    """Devices with enough keys should have number keys; small devices may use arrows only."""
    keymap = NAV_KEYMAPS[multi_controller.grid_key]
    nums = [k for k, v in keymap.items() if v[0] == "num"]
    if multi_controller.total_keys >= 15:
        assert len(nums) >= 2


def test_nav_keymap_keys_in_range(multi_controller):
    keymap = NAV_KEYMAPS[multi_controller.grid_key]
    for key_idx in keymap:
        assert 0 <= key_idx < multi_controller.total_keys, f"Key {key_idx} out of range"


def test_nav_styles_match_keymap(multi_controller):
    """Every key in the keymap should have a style entry."""
    keymap = NAV_KEYMAPS[multi_controller.grid_key]
    styles = NAV_STYLES[multi_controller.grid_key]
    for key_idx in keymap:
        assert key_idx in styles, f"Key {key_idx} has keymap entry but no style"


# --- Layout fallback ---

def test_layout_fallback_to_default(multi_controller):
    """Unknown layout name should fall back to default for any device."""
    multi_controller.config["layout"] = "triple_mega_quad"
    layout = multi_controller._get_layout()
    expected = LAYOUTS[multi_controller.grid_key]["default"]
    assert layout == expected


def test_available_layouts(multi_controller):
    available = multi_controller._get_available_layouts()
    assert "default" in available
    assert len(available) >= 2  # every device has at least default + quad


# --- Quad layout merged zones ---

def test_quad_layout_has_merged_terminal(multi_controller):
    """Quad layout should have T1 spanning 4 keys (2x2 merge)."""
    multi_controller.config["layout"] = "quad"
    layout = multi_controller._get_layout()
    t1_count = layout.count("T1")
    assert t1_count == 4, f"T1 appears {t1_count} times, expected 4 (2x2 merge)"
