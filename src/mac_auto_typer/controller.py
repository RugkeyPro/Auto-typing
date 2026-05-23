from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from .core import TypingOptions, TypingProgress, TypingSession, TypingState
from .input_blocker import InputBlocker
from .typing_backend import TyperBackend


ProgressCallback = Callable[[TypingProgress], None]


class AutoTyperController:
    def __init__(
        self,
        backend: TyperBackend,
        options: TypingOptions | None = None,
        on_progress: Optional[ProgressCallback] = None,
        on_character: Optional[Callable[[str], None]] = None,
        input_blocker: InputBlocker | None = None,
    ) -> None:
        self._backend = backend
        self._options = options or TypingOptions()
        self._on_progress = on_progress
        self._on_character = on_character
        self._input_blocker = input_blocker
        self._input_blocking = False
        self._session = TypingSession()
        self._lock = threading.RLock()
        self._pause_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._worker: threading.Thread | None = None

    def set_text(self, text: str, keep_position: bool = True) -> None:
        with self._lock:
            if self._session.state == TypingState.RUNNING:
                return
            self._session.set_text(text, keep_position=keep_position)
            progress = self._session.snapshot()
        self._emit(progress)

    def set_delay_ms(self, delay_ms: int) -> None:
        with self._lock:
            self._options.delay_ms = delay_ms

    def set_jitter_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._options.jitter_percent = 15 if enabled else 0

    def start_or_resume(self) -> None:
        with self._lock:
            started = self._session.start_or_resume()
            progress = self._session.snapshot()
            if not started:
                self._emit(progress)
                return
            self._pause_event.clear()

        try:
            self._set_input_blocking(True)
        except Exception as exc:
            with self._lock:
                self._session.fail(str(exc))
                progress = self._session.snapshot()
            self._emit(progress)
            return

        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(
                    target=self._run_loop,
                    name="AutoTyperWorker",
                    daemon=True,
                )
                self._worker.start()
        self._emit(progress)

    def pause(self) -> None:
        with self._lock:
            self._session.pause()
            self._pause_event.set()
            progress = self._session.snapshot()
        self._set_input_blocking(False)
        self._emit(progress)

    def reset(self) -> None:
        with self._lock:
            self._session.reset()
            self._pause_event.set()
            progress = self._session.snapshot()
        self._set_input_blocking(False)
        self._emit(progress)

    def clear(self) -> None:
        with self._lock:
            self._session.clear()
            self._pause_event.set()
            progress = self._session.snapshot()
        self._set_input_blocking(False)
        self._emit(progress)

    def snapshot(self) -> TypingProgress:
        with self._lock:
            return self._session.snapshot()

    def wait_for_state(self, state: TypingState, timeout: float = 2.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.snapshot().state == state:
                return True
            time.sleep(0.01)
        return self.snapshot().state == state

    def shutdown(self) -> None:
        self._shutdown_event.set()
        self._pause_event.set()
        self._set_input_blocking(False)
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=1.0)

    def _run_loop(self) -> None:
        initial_delay = self._options.initial_delay_seconds()
        if initial_delay > 0 and self._pause_event.wait(initial_delay):
            return

        while not self._shutdown_event.is_set():
            with self._lock:
                next_item = self._session.peek_next()
                if next_item is None:
                    progress = self._session.snapshot()
                    should_exit = progress.state != TypingState.RUNNING
                else:
                    progress = self._session.snapshot()
                    should_exit = False
            self._emit(progress)

            if should_exit:
                self._set_input_blocking(False)
                return
            if next_item is None:
                time.sleep(0.01)
                continue

            if self._pause_event.is_set() or self._shutdown_event.is_set():
                continue

            position, character = next_item
            try:
                self._backend.send_character(character)
                if self._on_character:
                    self._on_character(character)
            except Exception as exc:  # pragma: no cover - platform dependent
                with self._lock:
                    self._session.fail(str(exc))
                    progress = self._session.snapshot()
                self._set_input_blocking(False)
                self._emit(progress)
                return

            with self._lock:
                self._session.mark_sent(position)
                progress = self._session.snapshot()
                delay_seconds = self._options.next_delay_seconds()
            self._emit(progress)

            if progress.state != TypingState.RUNNING:
                self._set_input_blocking(False)
                return
            if self._pause_event.wait(delay_seconds):
                continue

    def _emit(self, progress: TypingProgress) -> None:
        if self._on_progress:
            self._on_progress(progress)

    def _set_input_blocking(self, enabled: bool) -> None:
        if self._input_blocker is None or self._input_blocking == enabled:
            return
        self._input_blocker.set_blocking(enabled)
        self._input_blocking = enabled
