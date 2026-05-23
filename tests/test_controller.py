from __future__ import annotations

import unittest

from mac_auto_typer.controller import AutoTyperController
from mac_auto_typer.core import TypingOptions, TypingState
from mac_auto_typer.typing_backend import MockTyper


class RecordingInputBlocker:
    def __init__(self) -> None:
        self.states: list[bool] = []

    def start(self) -> None:
        return None

    def set_blocking(self, enabled: bool) -> None:
        self.states.append(enabled)

    def stop(self) -> None:
        self.states.append(False)


class FailingInputBlocker:
    def start(self) -> None:
        return None

    def set_blocking(self, enabled: bool) -> None:
        if enabled:
            raise RuntimeError("input blocking unavailable")

    def stop(self) -> None:
        return None


class AutoTyperControllerTests(unittest.TestCase):
    def test_controller_types_text_to_completion(self) -> None:
        backend = MockTyper()
        controller = AutoTyperController(
            backend,
            TypingOptions(delay_ms=10, jitter_percent=0, initial_delay_ms=0),
        )
        controller.set_text("\u4e2d\u6587abc", keep_position=False)
        controller.start_or_resume()
        self.assertTrue(controller.wait_for_state(TypingState.COMPLETED, timeout=2))
        self.assertEqual(backend.output, "\u4e2d\u6587abc")
        controller.shutdown()

    def test_duplicate_start_does_not_duplicate_output(self) -> None:
        backend = MockTyper()
        controller = AutoTyperController(
            backend,
            TypingOptions(delay_ms=10, jitter_percent=0, initial_delay_ms=0),
        )
        controller.set_text("abc", keep_position=False)
        controller.start_or_resume()
        controller.start_or_resume()
        self.assertTrue(controller.wait_for_state(TypingState.COMPLETED, timeout=2))
        self.assertEqual(backend.output, "abc")
        controller.shutdown()

    def test_on_character_callback_receives_typed_characters(self) -> None:
        backend = MockTyper()
        typed_chars: list[str] = []
        controller = AutoTyperController(
            backend,
            TypingOptions(delay_ms=10, jitter_percent=0, initial_delay_ms=0),
            on_character=typed_chars.append,
        )
        controller.set_text("hello", keep_position=False)
        controller.start_or_resume()
        self.assertTrue(controller.wait_for_state(TypingState.COMPLETED, timeout=2))
        self.assertEqual("".join(typed_chars), "hello")
        controller.shutdown()

    def test_input_blocker_locks_during_typing_and_unlocks_on_completion(self) -> None:
        backend = MockTyper()
        blocker = RecordingInputBlocker()
        controller = AutoTyperController(
            backend,
            TypingOptions(delay_ms=10, jitter_percent=0, initial_delay_ms=0),
            input_blocker=blocker,
        )
        controller.set_text("abc", keep_position=False)
        controller.start_or_resume()
        self.assertTrue(controller.wait_for_state(TypingState.COMPLETED, timeout=2))
        self.assertEqual(backend.output, "abc")
        self.assertEqual(blocker.states[0], True)
        self.assertEqual(blocker.states[-1], False)
        controller.shutdown()

    def test_input_blocker_failure_prevents_typing(self) -> None:
        backend = MockTyper()
        controller = AutoTyperController(
            backend,
            TypingOptions(delay_ms=10, jitter_percent=0, initial_delay_ms=0),
            input_blocker=FailingInputBlocker(),
        )
        controller.set_text("abc", keep_position=False)
        controller.start_or_resume()
        self.assertEqual(controller.snapshot().state, TypingState.ERROR)
        self.assertEqual(backend.output, "")
        controller.shutdown()


if __name__ == "__main__":
    unittest.main()
