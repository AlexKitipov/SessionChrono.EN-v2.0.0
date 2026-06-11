"""Source and PyInstaller entry point for SessionChrono."""

import argparse

from core.config import print_runtime_path_report


def main() -> None:
    parser = argparse.ArgumentParser(description="SessionChrono clipboard notepad")
    parser.add_argument(
        "--paths",
        action="store_true",
        help="Print resolved runtime paths without starting Tkinter.",
    )
    args = parser.parse_args()

    if args.paths:
        print_runtime_path_report()
        return

    from ui.tkinter_ui import start_app

    start_app()


if __name__ == "__main__":
    main()
