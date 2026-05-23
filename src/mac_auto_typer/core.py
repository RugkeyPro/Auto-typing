from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from typing import Optional


class TypingState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass(slots=True)
class TypingProgress:
    state: TypingState
    position: int
    total: int
    last_error: str = ""

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.position)


@dataclass(slots=True)
class TypingOptions:
    delay_ms: int = 120
    jitter_percent: int = 15
    initial_delay_ms: int = 250

    def normalized_delay_ms(self) -> int:
        return max(10, min(2000, int(self.delay_ms)))

    def normalized_jitter_percent(self) -> int:
        return max(0, min(80, int(self.jitter_percent)))

    def next_delay_seconds(self, rng: random.Random | None = None) -> float:
        base = self.normalized_delay_ms() / 1000.0
        jitter = self.normalized_jitter_percent() / 100.0
        if jitter <= 0:
            return base
        source = rng or random
        spread = base * jitter
        return max(0.01, source.uniform(base - spread, base + spread))

    def initial_delay_seconds(self) -> float:
        return max(0, min(3000, int(self.initial_delay_ms))) / 1000.0


class TypingSession:
    """Thread-safe callers should guard this object with their own lock."""

    def __init__(self) -> None:
        self._text = ""
        self._position = 0
        self._state = TypingState.IDLE
        self._last_error = ""

    @property
    def text(self) -> str:
        return self._text

    @property
    def position(self) -> int:
        return self._position

    @property
    def state(self) -> TypingState:
        return self._state

    def set_text(self, text: str, keep_position: bool = True) -> None:
        self._text = text or ""
        if keep_position:
            self._position = min(self._position, len(self._text))
        else:
            self._position = 0
        self._last_error = ""
        if not self._text:
            self._state = TypingState.IDLE
            self._position = 0
        elif self._position >= len(self._text):
            self._state = TypingState.COMPLETED
        elif self._state in {TypingState.COMPLETED, TypingState.ERROR}:
            self._state = TypingState.PAUSED

    def start_or_resume(self) -> bool:
        if not self._text:
            self._state = TypingState.IDLE
            return False
        if self._state == TypingState.COMPLETED:
            self._position = 0
        self._last_error = ""
        self._state = TypingState.RUNNING
        return True

    def pause(self) -> None:
        if self._state == TypingState.RUNNING:
            self._state = TypingState.PAUSED

    def reset(self) -> None:
        self._position = 0
        self._last_error = ""
        self._state = TypingState.IDLE if not self._text else TypingState.PAUSED

    def clear(self) -> None:
        self._text = ""
        self._position = 0
        self._last_error = ""
        self._state = TypingState.IDLE

    def peek_next(self) -> Optional[tuple[int, str]]:
        if self._state != TypingState.RUNNING:
            return None
        if self._position >= len(self._text):
            self._state = TypingState.COMPLETED
            return None
        return self._position, self._text[self._position]

    def mark_sent(self, position: int) -> None:
        if position != self._position:
            return
        self._position += 1
        if self._position >= len(self._text):
            self._state = TypingState.COMPLETED

    def fail(self, message: str) -> None:
        self._last_error = message
        self._state = TypingState.ERROR

    def snapshot(self) -> TypingProgress:
        return TypingProgress(
            state=self._state,
            position=self._position,
            total=len(self._text),
            last_error=self._last_error,
        )
