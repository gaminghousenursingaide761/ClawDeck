"""Regression tests for resilient hook-source detection."""

import pytest

from install_hooks import is_our_entry


@pytest.mark.parametrize("entry", [None, {}, {"hooks": None}, {"hooks": [None, "not-a-hook"]}])
def test_is_our_entry_ignores_malformed_or_empty_hook_entries(entry):
    """Malformed persisted settings must not abort hook merging."""
    assert is_our_entry(entry) is False
