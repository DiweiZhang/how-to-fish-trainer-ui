import os
import sys
import argparse

# Protect against PyInstaller --windowed mode where stdout/stderr are None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

if sys.platform == "win32":
    try:
        import ctypes
        if len(sys.argv) > 1:
            ctypes.windll.kernel32.AttachConsole(-1)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .trainer import HowToFishTrainer
from .ui.gui import run_gui


def main():
    parser = argparse.ArgumentParser(description="How to Fish - External Unity Mono Trainer")
    parser.add_argument(
        "--process",
        "-p",
        default="How to Fish.exe",
        help="Target process executable name (default: 'How to Fish.exe')",
    )
    parser.add_argument(
        "--lang",
        "-l",
        choices=["zh", "en"],
        default="zh",
        help="Initial interface language: 'zh' (Chinese) or 'en' (English) (default: 'zh')",
    )
    parser.add_argument(
        "--console",
        "--cli",
        action="store_true",
        help="Run in classic terminal console dashboard mode instead of GUI",
    )
    args = parser.parse_args()

    if args.console:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.AttachConsole(-1)
                sys.stdout.reconfigure(encoding="utf-8")
                sys.stderr.reconfigure(encoding="utf-8")
            except Exception:
                pass
        trainer = HowToFishTrainer(process_name=args.process, language=args.lang)
        try:
            trainer.run()
        except KeyboardInterrupt:
            trainer.stop()
            sys.exit(0)
    else:
        run_gui(process_name=args.process, language=args.lang)


if __name__ == "__main__":
    main()

