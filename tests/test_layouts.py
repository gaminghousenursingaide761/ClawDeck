import pytest
from main import (
    LAYOUTS, LAYOUT_NAMES, COLS, ROWS, ENTER_KEY_INDEX, GRID_SLOTS, TOTAL_KEYS,
    DEVICE_PROFILES, _layout_names_for_grid,
)


# --- Layout registry structure ---

def test_all_layouts_correct_length():
    """Every layout array must have cols*rows elements for its grid size."""
    for grid_key, grid_layouts in LAYOUTS.items():
        cols, rows = grid_key
        expected = cols * rows
        for name, layout in grid_layouts.items():
            assert len(layout) == expected, (
                f"Layout '{name}' for {cols}x{rows} has {len(layout)} elements, expected {expected}"
            )


def test_all_layouts_end_with_enter():
    for grid_key, grid_layouts in LAYOUTS.items():
        for name, layout in grid_layouts.items():
            assert layout[-1] == "ENTER", (
                f"Layout '{name}' for {grid_key} last element is '{layout[-1]}', expected 'ENTER'"
            )


def test_all_supported_grids_have_layouts():
    """Every device profile must have a layout set."""
    for grid_key in DEVICE_PROFILES:
        assert grid_key in LAYOUTS, f"No layouts defined for {grid_key}"


def test_all_grids_have_default_layout():
    for grid_key in LAYOUTS:
        assert "default" in LAYOUTS[grid_key], f"No 'default' layout for {grid_key}"


def test_layout_names_helper():
    assert _layout_names_for_grid((5, 3)) == list(LAYOUTS[(5, 3)].keys())


def test_backward_compat_layout_names():
    """LAYOUT_NAMES should be the 5x3 layout names for backward compat."""
    assert set(LAYOUT_NAMES) == set(LAYOUTS[(5, 3)].keys())


# --- Terminal name helpers (5x3 default) ---

def test_get_terminal_names_excludes_enter(controller):
    names = controller._get_terminal_names()
    assert "ENTER" not in names


def test_get_terminal_names_unique(controller):
    names = controller._get_terminal_names()
    assert len(names) == len(set(names))


def test_get_terminal_names_default_has_14(controller):
    controller.config["layout"] = "default"
    names = controller._get_terminal_names()
    assert len(names) == 14


# --- Terminal slot helpers ---

def test_get_terminal_slots_covers_all_keys(controller):
    controller.config["layout"] = "default"
    slots = controller._get_terminal_slots()
    all_slot_keys = set()
    for key_list in slots.values():
        all_slot_keys.update(key_list)
    expected = set(range(controller.total_keys)) - {controller.enter_key_index}
    assert all_slot_keys == expected


# --- Key ↔ terminal resolution ---

def test_key_to_terminal_enter_is_none(controller):
    controller.config["layout"] = "default"
    result = controller._key_to_terminal(controller.enter_key_index)
    assert result is None


def test_key_to_terminal_valid_keys(controller):
    controller.config["layout"] = "default"
    for key in range(controller.total_keys - 1):
        result = controller._key_to_terminal(key)
        assert result is not None, f"Key {key} returned None, expected a terminal name"


def test_terminal_to_active_slot_returns_first_key(controller):
    controller.config["layout"] = "default"
    assert controller._terminal_to_active_slot("T1") == 0
    assert controller._terminal_to_active_slot("T2") == 1


# --- Grid geometry ---

def test_grid_rect_corners(controller):
    screen = controller.screen
    sx, sy, sw, sh = screen["x"], screen["y"], screen["w"], screen["h"]

    rect0 = controller._grid_rect(0)
    assert rect0["x"] == sx
    assert rect0["y"] == sy

    rect_last_col = controller._grid_rect(controller.cols - 1)
    assert rect_last_col["x"] + rect_last_col["w"] == sx + sw

    rect_enter = controller._grid_rect(controller.enter_key_index)
    assert rect_enter["x"] + rect_enter["w"] == sx + sw
    # Allow ±1 for int truncation rounding in grid calculations
    assert abs((rect_enter["y"] + rect_enter["h"]) - (sy + sh)) <= 1


def test_grid_rect_dimensions(controller):
    screen = controller.screen
    cell_w = screen["w"] / controller.cols
    cell_h = screen["h"] / controller.rows

    for key in range(controller.total_keys):
        rect = controller._grid_rect(key)
        assert abs(rect["w"] - cell_w) < 1, f"Key {key} width {rect['w']} != {cell_w}"
        assert abs(rect["h"] - cell_h) < 1, f"Key {key} height {rect['h']} != {cell_h}"


def test_get_terminal_rect_merged(controller):
    controller.config["layout"] = "quad"
    screen = controller.screen

    # In "quad" layout, first 4 keys (0,1,5,6) are "T1" — a 2x2 merged zone
    rect = controller._get_terminal_rect("T1")

    expected_w = (screen["w"] / controller.cols) * 2
    expected_h = (screen["h"] / controller.rows) * 2

    assert abs(rect["w"] - expected_w) < 2, f"T1 width {rect['w']} != {expected_w}"
    assert abs(rect["h"] - expected_h) < 2, f"T1 height {rect['h']} != {expected_h}"


def test_layout_switch(controller):
    controller.config["layout"] = "default"
    default_layout = controller._get_layout()

    controller.config["layout"] = "quad"
    quad_layout = controller._get_layout()

    assert default_layout != quad_layout
    assert quad_layout == LAYOUTS[(5, 3)]["quad"]


def test_layout_fallback_for_missing_layout(controller):
    """Requesting a layout that doesn't exist falls back to default."""
    controller.config["layout"] = "nonexistent_layout"
    layout = controller._get_layout()
    assert layout == LAYOUTS[(5, 3)]["default"]
