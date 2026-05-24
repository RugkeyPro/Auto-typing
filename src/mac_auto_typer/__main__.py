from __future__ import annotations

import sys


def main() -> int:
    if "--self-test" in sys.argv:
        return 0
    from mac_auto_typer.app import run

    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
