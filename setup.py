"""
py2app build script for ClawDeck.

Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ["menubar.py"]
DATA_FILES = ["settings.html"]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "ClawDeck",
        "CFBundleDisplayName": "ClawDeck",
        "CFBundleIdentifier": "com.clawdeck.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,  # menu bar app — no dock icon
        "NSAppleEventsUsageDescription": "ClawDeck needs to control terminal windows.",
        "NSAccessibilityUsageDescription": "ClawDeck needs accessibility access for window management and keystroke sending.",
    },
    "packages": ["rumps", "StreamDeck", "PIL"],
    "includes": [
        "main",
        "overlay",
        "Quartz",
        "CoreFoundation",
        "objc",
        "AppKit",
        "Foundation",
    ],
    "resources": ["deck-hook.sh", "install_hooks.py", "claude-hooks.json"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
