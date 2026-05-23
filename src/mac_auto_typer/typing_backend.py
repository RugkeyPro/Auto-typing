from __future__ import annotations

from dataclasses import dataclass, field
import platform
import time
from typing import Protocol


SOFTWARE_EVENT_MARKER = 0x4D415459


class TyperBackend(Protocol):
    def send_character(self, character: str) -> None:
        """Send exactly one character to the active application."""


@dataclass
class MockTyper:
    """Development backend used on non-macOS systems and in tests."""

    sent: list[str] = field(default_factory=list)

    def send_character(self, character: str) -> None:
        self.sent.append(character)

    @property
    def output(self) -> str:
        return "".join(self.sent)

    def clear(self) -> None:
        self.sent.clear()


class MacQuartzTyper:
    """macOS Quartz event backend.

    The import is intentionally lazy so Windows development can run tests
    without PyObjC installed.
    """

    def __init__(self, post_delay_seconds: float = 0.002) -> None:
        self._post_delay_seconds = post_delay_seconds
        self._source = None

    def _event_source(self, quartz):  # noqa: ANN001
        if self._source is None:
            self._source = quartz.CGEventSourceCreate(quartz.kCGEventSourceStatePrivate)
            try:
                quartz.CGEventSourceSetUserData(self._source, SOFTWARE_EVENT_MARKER)
            except Exception:
                pass
        return self._source

    def send_character(self, character: str) -> None:
        if not character:
            return
        import Quartz  # type: ignore[import-not-found]

        source = self._event_source(Quartz)
        utf16_units = len(character.encode("utf-16-le")) // 2
        down_event = Quartz.CGEventCreateKeyboardEvent(source, 0, True)
        Quartz.CGEventKeyboardSetUnicodeString(down_event, utf16_units, character)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, down_event)

        if self._post_delay_seconds > 0:
            time.sleep(self._post_delay_seconds)

        up_event = Quartz.CGEventCreateKeyboardEvent(source, 0, False)
        Quartz.CGEventKeyboardSetUnicodeString(up_event, utf16_units, character)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, up_event)


def default_backend() -> TyperBackend:
    if platform.system() == "Darwin":
        return MacQuartzTyper()
    return MockTyper()
