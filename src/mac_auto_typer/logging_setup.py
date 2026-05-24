from __future__ import annotations

import logging
from pathlib import Path
import sys
import traceback


def setup_logging() -> Path:
    log_dir = Path.home() / "Library" / "Logs" / "MacAutoTyper"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "MacAutoTyper.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.info("MacAutoTyper starting")

    def handle_exception(exc_type, exc_value, exc_traceback):  # noqa: ANN001
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical(
            "Unhandled exception:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )

    sys.excepthook = handle_exception
    return log_path
