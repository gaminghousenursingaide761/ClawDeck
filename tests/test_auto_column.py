"""Tests for Auto-Column feature."""
import pytest
from unittest.mock import patch, call, MagicMock
from main import DeckController


def _make(cols=5, rows=3):
    """Create a DeckController with given grid size, OS/hardware deps patched."""
    with patch.object(DeckController, '_get_screen_bounds',
                      return_value={'x': 0, 'y': 25, 'w': 2560, 'h': 1415}):
        with patch.object(DeckController, '_init_fonts'):
            c = DeckController()
            c._init_grid(cols, rows)
            c.screen = {'x': 0, 'y': 25, 'w': 2560, 'h': 1415}
            c.font_xs = c.font_sm = c.font_md = c.font_lg = None
            return c


class TestGetColumnRect:
    """_get_column_rect returns full-height rect for a slot's column."""

    def test_single_cell_default_layout(self):
        """Slot 1 (T2, column 1) in default 5x3 layout -> full height, one column wide."""
        c = _make(5, 3)
        c.config["layout"] = "default"
        rect = c._get_column_rect(1)
        # Column 1: x = 2560/5 * 1 = 512, w = 512
        # Full height: y = 25, h = 1415
        assert rect["x"] == 512
        assert rect["y"] == 25
        assert rect["w"] == 512
        assert rect["h"] == 1415

    def test_merged_terminal_quad_layout(self):
        """T1 spans cols 0-1 in quad layout -> full height, two columns wide."""
        c = _make(5, 3)
        c.config["layout"] = "quad"
        # Slot 0 is T1 in quad, which occupies slots 0,1,5,6 (cols 0-1, rows 0-1)
        rect = c._get_column_rect(0)
        # Columns 0-1: x = 0, w = 2 * 512 = 1024
        # Full height: y = 25, h = 1415
        assert rect["x"] == 0
        assert rect["y"] == 25
        assert rect["w"] == 1024
        assert rect["h"] == 1415

    def test_last_column_before_enter(self):
        """Slot 3 (T4, column 3) in default layout -> correct column rect."""
        c = _make(5, 3)
        c.config["layout"] = "default"
        rect = c._get_column_rect(3)
        # Column 3: x = 512 * 3 = 1536, w = 512
        assert rect["x"] == 1536
        assert rect["w"] == 512
        assert rect["h"] == 1415

    def test_mini_device(self):
        """Slot 0 on 3x2 Mini -> full height, one column wide."""
        c = _make(3, 2)
        c.config["layout"] = "default"
        rect = c._get_column_rect(0)
        # Column 0: x = 0, w = 2560/3 = 853
        # Full height: y = 25, h = 1415
        assert rect["x"] == 0
        assert rect["y"] == 25
        assert rect["w"] == 853
        assert rect["h"] == 1415

    def test_enter_slot_returns_none(self):
        """ENTER slot has no terminal -- returns None."""
        c = _make(5, 3)
        c.config["layout"] = "default"
        result = c._get_column_rect(14)
        assert result is None

    def test_none_slot_returns_none(self):
        """None slot (no terminal focused) -- returns None."""
        c = _make(5, 3)
        result = c._get_column_rect(None)
        assert result is None


class TestApplyAutoColumn:
    """_apply_auto_column expands/shrinks windows via _move_window_to_rect."""

    def _setup_controller(self):
        c = _make(5, 3)
        c.config["auto_column"] = True
        # Simulate known window positions (Quartz-style window dicts)
        # Window at slot 0 (T1): grid rect for slot 0
        r0 = c._grid_rect(0)
        c._last_term_wins = [
            {"owner": "Terminal", "id": 100, "x": r0["x"], "y": r0["y"], "w": r0["w"], "h": r0["h"]},
        ]
        # Window at slot 1 (T2): grid rect for slot 1
        r1 = c._grid_rect(1)
        c._last_term_wins.append(
            {"owner": "Terminal", "id": 101, "x": r1["x"], "y": r1["y"], "w": r1["w"], "h": r1["h"]},
        )
        return c

    @patch.object(DeckController, '_move_window_to_rect')
    def test_expand_new_active(self, mock_move):
        """Switching to a slot expands that window to column rect."""
        c = self._setup_controller()
        mock_move.reset_mock()
        c._apply_auto_column(None, 0)
        # Should expand slot 0's window to column rect
        col_rect = c._get_column_rect(0)
        mock_move.assert_called_once()
        call_args = mock_move.call_args
        assert call_args[0][1] == col_rect
        assert c._auto_column_slot == 0

    @patch.object(DeckController, '_move_window_to_rect')
    def test_shrink_old_expand_new(self, mock_move):
        """Switching from slot A to slot B: shrink A, expand B."""
        c = self._setup_controller()
        c._auto_column_slot = 0
        # Update slot 0's window to look expanded (column rect)
        col0 = c._get_column_rect(0)
        c._last_term_wins[0] = {"owner": "Terminal", "id": 100, "x": col0["x"], "y": col0["y"], "w": col0["w"], "h": col0["h"]}
        mock_move.reset_mock()
        c._apply_auto_column(0, 1)
        assert mock_move.call_count == 2
        assert c._auto_column_slot == 1

    @patch.object(DeckController, '_move_window_to_rect')
    def test_shrink_on_focus_leave(self, mock_move):
        """Leaving terminals (new_slot=None) shrinks the expanded window."""
        c = self._setup_controller()
        c._auto_column_slot = 0
        col0 = c._get_column_rect(0)
        c._last_term_wins[0] = {"owner": "Terminal", "id": 100, "x": col0["x"], "y": col0["y"], "w": col0["w"], "h": col0["h"]}
        mock_move.reset_mock()
        c._apply_auto_column(0, None)
        # Should shrink slot 0 back to grid rect
        mock_move.assert_called_once()
        grid_rect = c._get_terminal_rect(c._key_to_terminal(0))
        assert mock_move.call_args[0][1] == grid_rect
        assert c._auto_column_slot is None

    @patch.object(DeckController, '_move_window_to_rect')
    def test_noop_when_disabled(self, mock_move):
        """Does nothing when auto_column is False."""
        c = self._setup_controller()
        c.config["auto_column"] = False
        mock_move.reset_mock()
        c._apply_auto_column(None, 0)
        mock_move.assert_not_called()
        assert c._auto_column_slot is None
