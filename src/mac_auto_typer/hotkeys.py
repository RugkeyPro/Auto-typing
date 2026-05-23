from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class HotkeyError(RuntimeError):
    pass


@dataclass(slots=True)
class HotkeyBindings:
    start_resume: str = "<ctrl>+1"
    pause: str = "<ctrl>+2"


class GlobalHotkeyManager:
    def __init__(
        self,
        on_start_resume: Callable[[], None],
        on_pause: Callable[[], None],
        bindings: HotkeyBindings | None = None,
    ) -> None:
        self._on_start_resume = on_start_resume
        self._on_pause = on_pause
        self._bindings = bindings or HotkeyBindings()
        self._listener = None

    @property
    def bindings(self) -> HotkeyBindings:
        return self._bindings

    def start(self) -> None:
        if self._listener is not None:
            return
        try:
            from pynput import keyboard
        except Exception as exc:  # pragma: no cover - import depends on env
            raise HotkeyError(f"Cannot import pynput keyboard listener: {exc}") from exc

        self._listener = keyboard.GlobalHotKeys(
            {
                self._bindings.start_resume: self._safe_start_resume,
                self._bindings.pause: self._safe_pause,
            }
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None

    def _safe_start_resume(self) -> None:
        try:
            self._on_start_resume()
        except Exception:
            pass

    def _safe_pause(self) -> None:
        try:
            self._on_pause()
        except Exception:
            pass
