# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path


ROOT = Path(SPECPATH).parents[1]
ENTRYPOINT = ROOT / "build" / "macos" / "pyinstaller_entry.py"


a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
        "pynput._util.darwin",
        "Quartz",
        "ApplicationServices",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MacAutoTyper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MacAutoTyper",
)
app = BUNDLE(
    coll,
    name="MacAutoTyper.app",
    icon=None,
    bundle_identifier="com.local.macautotyper",
    info_plist={
        "CFBundleName": "MacAutoTyper",
        "CFBundleDisplayName": "MacAutoTyper",
        "NSAppleEventsUsageDescription": "MacAutoTyper posts user-controlled keyboard events to the active app.",
        "NSInputMonitoringUsageDescription": "MacAutoTyper listens for Ctrl+1 and Ctrl+2 global hotkeys.",
        "NSHumanReadableCopyright": "Internal use.",
    },
)
