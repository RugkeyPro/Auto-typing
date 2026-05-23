from __future__ import annotations

from pathlib import Path


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md"}


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_text_file(path: str | Path) -> str:
    file_path = Path(path)
    try:
        return normalize_text(file_path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        return normalize_text(file_path.read_text(encoding="gb18030"))


def is_supported_text_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_TEXT_SUFFIXES
