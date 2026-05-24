from __future__ import annotations

import argparse
import os
import importlib
import platform
import subprocess
import sys
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def import_module(name: str) -> None:
    importlib.import_module(name)
    print(f"ok: imported {name}")


def check_runtime() -> None:
    require(platform.system() == "Darwin", "macOS smoke check must run on macOS")
    print(f"ok: platform {platform.platform()}")
    print(f"ok: python {sys.version.split()[0]}")


def check_dependencies() -> None:
    for module_name in [
        "PySide6",
        "Quartz",
        "pynput.keyboard",
        "mac_auto_typer.app",
        "mac_auto_typer.input_blocker",
        "mac_auto_typer.typing_backend",
    ]:
        import_module(module_name)


def check_backend_selection() -> None:
    from mac_auto_typer.input_blocker import MacKeyboardInputBlocker, default_input_blocker
    from mac_auto_typer.typing_backend import MacQuartzTyper, default_backend

    backend = default_backend()
    blocker = default_input_blocker(lambda: None)
    require(isinstance(backend, MacQuartzTyper), "default backend is not MacQuartzTyper")
    require(
        isinstance(blocker, MacKeyboardInputBlocker),
        "default input blocker is not MacKeyboardInputBlocker",
    )
    print("ok: macOS backend selection")


def check_controller_with_mock() -> None:
    from mac_auto_typer.controller import AutoTyperController
    from mac_auto_typer.core import TypingOptions, TypingState
    from mac_auto_typer.typing_backend import MockTyper

    backend = MockTyper()
    controller = AutoTyperController(
        backend,
        TypingOptions(delay_ms=10, jitter_percent=0, initial_delay_ms=0),
    )
    controller.set_text("mac smoke", keep_position=False)
    controller.start_or_resume()
    require(
        controller.wait_for_state(TypingState.COMPLETED, timeout=2),
        "mock controller did not complete",
    )
    require(backend.output == "mac smoke", "mock controller output mismatch")
    controller.shutdown()
    print("ok: controller mock typing")


def check_app_bundle(path: Path | None) -> None:
    if path is None:
        return
    require(path.exists(), f"app bundle does not exist: {path}")
    require((path / "Contents" / "Info.plist").exists(), "Info.plist missing")
    executable = path / "Contents" / "MacOS" / "MacAutoTyper"
    require(executable.exists(), f"main executable missing: {executable}")
    require(executable.stat().st_mode & 0o111, f"main executable is not executable: {executable}")
    print(f"ok: app bundle exists at {path}")


def check_app_executable(path: Path | None) -> None:
    if path is None:
        return
    executable = path / "Contents" / "MacOS" / "MacAutoTyper"
    env = os.environ.copy()
    env["MAC_AUTO_TYPER_SELF_TEST"] = "1"
    result = subprocess.run(
        [str(executable)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    require(
        result.returncode == 0,
        f"app executable self-test failed with exit code {result.returncode}",
    )
    print("ok: app executable self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-bundle", type=Path, default=None)
    args = parser.parse_args()

    check_runtime()
    check_dependencies()
    check_backend_selection()
    check_controller_with_mock()
    check_app_bundle(args.app_bundle)
    check_app_executable(args.app_bundle)

    print("macOS smoke check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
