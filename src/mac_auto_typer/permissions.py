from __future__ import annotations

import platform


def is_macos() -> bool:
    return platform.system() == "Darwin"


def check_accessibility(prompt: bool = False) -> tuple[bool, str]:
    if not is_macos():
        return True, "Windows/Linux development mode: system typing is mocked."

    try:
        import Quartz  # type: ignore[import-not-found]

        trusted = bool(
            Quartz.AXIsProcessTrustedWithOptions(
                {Quartz.kAXTrustedCheckOptionPrompt: bool(prompt)}
            )
        )
    except Exception as exc:  # pragma: no cover - platform dependent
        return False, f"Cannot check macOS Accessibility permission: {exc}"

    if trusted:
        return True, "macOS Accessibility permission is enabled."
    return (
        False,
        "Enable Accessibility and Input Monitoring for MacAutoTyper in System Settings.",
    )
