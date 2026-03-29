"""Shared fixtures for ClawDeck tests.

main.py imports macOS-only modules (Quartz, AppKit, StreamDeck) at module level.
We mock these before importing so tests can run on any platform and without hardware.
"""
import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock macOS-only modules before importing main
_mock_modules = [
    "Quartz", "CoreFoundation",
    "StreamDeck", "StreamDeck.DeviceManager", "StreamDeck.ImageHelpers",
    "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
    "rumps",
]

for mod in _mock_modules:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Now we can import from main
from main import (
    DeckController, CONFIG_DEFAULTS, LAYOUTS, LAYOUT_NAMES,
    _rgb_to_hex, _hex_to_rgb, _format_keystroke,
    COLS, ROWS, ENTER_KEY_INDEX, GRID_SLOTS, TOTAL_KEYS,
    MODE_GRID, MODE_NAV,
    COLOR_BG_ACTIVE, COLOR_BG_IDLE, COLOR_BG_WORKING, COLOR_BG_PERMISSION,
    COLOR_BG_DEFAULT, COLOR_FG_DEFAULT,
    NAV_BUTTON_STYLES, NAV_KEYMAPS, NAV_STYLES, DEVICE_PROFILES,
    _layout_names_for_grid,
)


def _make_controller(cols=5, rows=3):
    """Create a DeckController with given grid size, OS/hardware deps patched."""
    with patch.object(DeckController, '_get_screen_bounds',
                      return_value={'x': 0, 'y': 25, 'w': 2560, 'h': 1415}):
        with patch.object(DeckController, '_init_fonts'):
            c = DeckController()
            c._init_grid(cols, rows)
            c.screen = {'x': 0, 'y': 25, 'w': 2560, 'h': 1415}
            c.font_xs = c.font_sm = c.font_md = c.font_lg = None
            return c


@pytest.fixture
def controller():
    """DeckController with OS/hardware deps patched out (5x3 default)."""
    return _make_controller(5, 3)


@pytest.fixture(params=[(5, 3), (3, 2), (8, 4), (4, 2)],
                ids=["5x3", "3x2", "8x4", "4x2"])
def multi_controller(request):
    """DeckController parametrized across all supported grid sizes."""
    cols, rows = request.param
    return _make_controller(cols, rows)


@pytest.fixture
def default_config():
    """A fresh copy of CONFIG_DEFAULTS."""
    import copy
    return copy.deepcopy(CONFIG_DEFAULTS)
