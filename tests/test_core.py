from __future__ import annotations

import random
import unittest

from mac_auto_typer.core import TypingOptions, TypingSession, TypingState
from mac_auto_typer.text_io import is_supported_text_file, normalize_text, read_text_file


class TypingSessionTests(unittest.TestCase):
    def test_mark_sent_advances_only_after_success(self) -> None:
        session = TypingSession()
        session.set_text("abc", keep_position=False)
        self.assertTrue(session.start_or_resume())
        item = session.peek_next()
        self.assertEqual(item, (0, "a"))
        session.mark_sent(0)
        self.assertEqual(session.snapshot().position, 1)
        self.assertEqual(session.peek_next(), (1, "b"))

    def test_pause_and_resume_continue_from_same_position(self) -> None:
        session = TypingSession()
        session.set_text("abcdef", keep_position=False)
        session.start_or_resume()
        position, _ = session.peek_next() or (-1, "")
        session.mark_sent(position)
        session.pause()
        self.assertEqual(session.snapshot().state, TypingState.PAUSED)
        self.assertEqual(session.snapshot().position, 1)
        session.start_or_resume()
        self.assertEqual(session.peek_next(), (1, "b"))

    def test_completed_restart_resets_to_beginning(self) -> None:
        session = TypingSession()
        session.set_text("a", keep_position=False)
        session.start_or_resume()
        session.mark_sent(0)
        self.assertEqual(session.snapshot().state, TypingState.COMPLETED)
        session.start_or_resume()
        self.assertEqual(session.snapshot().position, 0)
        self.assertEqual(session.snapshot().state, TypingState.RUNNING)

    def test_keep_position_clamps_when_text_is_shortened(self) -> None:
        session = TypingSession()
        session.set_text("abcdef", keep_position=False)
        session.start_or_resume()
        for index in range(4):
            session.mark_sent(index)
        session.pause()
        session.set_text("xy", keep_position=True)
        progress = session.snapshot()
        self.assertEqual(progress.position, 2)
        self.assertEqual(progress.state, TypingState.COMPLETED)


class TypingOptionsTests(unittest.TestCase):
    def test_delay_without_jitter_is_stable(self) -> None:
        options = TypingOptions(delay_ms=150, jitter_percent=0)
        self.assertEqual(options.next_delay_seconds(), 0.15)

    def test_delay_with_jitter_stays_in_expected_range(self) -> None:
        options = TypingOptions(delay_ms=100, jitter_percent=20)
        rng = random.Random(123)
        values = [options.next_delay_seconds(rng) for _ in range(20)]
        self.assertTrue(all(0.08 <= value <= 0.12 for value in values))


class TextIoTests(unittest.TestCase):
    def test_supported_text_suffixes(self) -> None:
        self.assertTrue(is_supported_text_file("note.txt"))
        self.assertTrue(is_supported_text_file("draft.MD"))
        self.assertFalse(is_supported_text_file("doc.docx"))

    def test_read_text_file_utf8_sig(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("\u4e2d\u6587abc", encoding="utf-8-sig")
            self.assertEqual(read_text_file(path), "\u4e2d\u6587abc")

    def test_normalize_text_collapses_windows_newlines(self) -> None:
        self.assertEqual(normalize_text("a\r\nb\rc"), "a\nb\nc")


if __name__ == "__main__":
    unittest.main()
