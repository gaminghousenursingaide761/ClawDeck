"""Tests for Ghostty TTY resolution via CWD matching."""
from unittest.mock import patch, MagicMock


def test_build_tty_map_skips_none_ttys(controller):
    """_build_tty_map should skip windows with tty=None (unresolved Ghostty windows)."""
    def fake_get_ttys(app):
        if app == "Ghostty":
            return [
                {"x": 150, "y": 200, "w": 500, "h": 400, "tty": "ttys001"},
                {"x": 700, "y": 200, "w": 500, "h": 400, "tty": None},
            ]
        return []

    with patch.object(controller, '_get_app_window_ttys', side_effect=fake_get_ttys):
        with patch.object(controller, '_resolve_tty_cwd', return_value="/tmp"):
            controller._build_tty_map()

    for slot, tty in controller.slot_tty.items():
        assert tty is not None, f"Slot {slot} has None TTY"


def _ghostty_run_side_effect(applescript_stdout, pgrep_children, child_ttys, child_cwds):
    """Build a subprocess.run side effect for Ghostty tests.

    Args:
        applescript_stdout: stdout from the osascript call (bounds + CWD)
        pgrep_children: dict of parent_pid -> list of child pids (for pgrep -P)
        child_ttys: dict of pid -> tty name (for ps -o tty=)
        child_cwds: dict of pid -> cwd path (for lsof)
    """
    def side_effect(cmd, **kwargs):
        r = MagicMock()
        if cmd[0] == "osascript":
            r.returncode = 0
            r.stdout = applescript_stdout
            return r
        elif cmd[0] == "pgrep":
            if "-xi" in cmd:
                # pgrep -xi ghostty → return main Ghostty PID
                r.returncode = 0
                r.stdout = "12345\n"
            elif "-P" in cmd:
                # pgrep -P <parent> → return children
                parent = cmd[cmd.index("-P") + 1]
                children = pgrep_children.get(parent, [])
                if children:
                    r.returncode = 0
                    r.stdout = "\n".join(children) + "\n"
                else:
                    r.returncode = 1
                    r.stdout = ""
            return r
        elif cmd[0] == "ps":
            # ps -o tty= -p <pid>
            pid = cmd[cmd.index("-p") + 1]
            tty = child_ttys.get(pid, "??")
            r.returncode = 0
            r.stdout = tty + "\n"
            return r
        elif cmd[0] == "lsof":
            pid = cmd[cmd.index("-p") + 1]
            cwd = child_cwds.get(pid)
            if cwd:
                r.returncode = 0
                r.stdout = f"p{pid}\nn{cwd}\n"
            else:
                r.returncode = 1
                r.stdout = ""
            return r
        r.returncode = 1
        r.stdout = ""
        return r
    return side_effect


def test_ghostty_returns_tty_via_cwd_match(controller):
    """Ghostty windows get TTY resolved by matching CWD from AppleScript
    against CWD from shell processes."""
    side_effect = _ghostty_run_side_effect(
        applescript_stdout="100,200,900,700,/Users/cory/project-a\n300,200,1100,700,/Users/cory/project-b\n",
        # ghostty(12345) → login(100,101) → shell(501,502)
        pgrep_children={
            "12345": ["100", "101"],
            "100": ["501"],
            "101": ["502"],
        },
        child_ttys={
            "100": "ttys001", "501": "ttys001",
            "101": "ttys002", "502": "ttys002",
        },
        child_cwds={
            "501": "/Users/cory/project-a",
            "502": "/Users/cory/project-b",
        },
    )

    with patch("subprocess.run", side_effect=side_effect):
        result = controller._get_app_window_ttys("Ghostty")

    assert len(result) == 2
    assert result[0]["tty"] == "ttys001"
    assert result[0]["x"] == 100
    assert result[0]["w"] == 800
    assert result[1]["tty"] == "ttys002"


def test_ghostty_duplicate_cwd_skips_second(controller):
    """When two Ghostty windows share the same CWD, only the first gets a TTY."""
    side_effect = _ghostty_run_side_effect(
        applescript_stdout="100,200,900,700,/Users/cory/same-dir\n300,200,1100,700,/Users/cory/same-dir\n",
        pgrep_children={
            "12345": ["100", "101"],
            "100": ["501"],
            "101": ["502"],
        },
        child_ttys={
            "100": "ttys001", "501": "ttys001",
            "101": "ttys002", "502": "ttys002",
        },
        child_cwds={
            "501": "/Users/cory/same-dir",
            "502": "/Users/cory/same-dir",
        },
    )

    with patch("subprocess.run", side_effect=side_effect):
        result = controller._get_app_window_ttys("Ghostty")

    # Both windows returned, but only one has a real TTY
    ttys_with_value = [w for w in result if w.get("tty")]
    assert len(ttys_with_value) == 1
    assert ttys_with_value[0]["tty"] == "ttys001"


def test_ghostty_no_windows_returns_empty(controller):
    """When Ghostty isn't running or has no windows, return empty list."""
    failed_result = MagicMock()
    failed_result.returncode = 1
    failed_result.stdout = ""

    with patch("subprocess.run", return_value=failed_result):
        result = controller._get_app_window_ttys("Ghostty")

    assert result == []


def test_ghostty_pgrep_fails_returns_empty(controller):
    """When pgrep can't find Ghostty process, return windows without TTYs."""
    applescript_result = MagicMock()
    applescript_result.returncode = 0
    applescript_result.stdout = "100,200,900,700,/Users/cory/project-a\n"

    def run_side_effect(cmd, **kwargs):
        if cmd[0] == "osascript":
            return applescript_result
        # All pgrep calls fail (including -P)
        r = MagicMock()
        r.returncode = 1
        r.stdout = ""
        return r

    with patch("subprocess.run", side_effect=run_side_effect):
        result = controller._get_app_window_ttys("Ghostty")

    # Window is returned but without TTY (tiling still works)
    assert len(result) == 1
    assert result[0].get("tty") is None
