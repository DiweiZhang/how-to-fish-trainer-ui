"""Build single standalone executable using PyInstaller with CustomTkinter GUI support."""

import argparse
import subprocess
import sys


def build(console: bool = False):
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--console" if console else "--windowed",
        "--uac-admin",
        "--name",
        "HowToFishTrainer",
        "--paths",
        "src",
        "--collect-all",
        "customtkinter",
        "--optimize",
        "2",
        "--exclude-module",
        "unittest",
        "--exclude-module",
        "doctest",
        "--exclude-module",
        "pydoc",
        "--exclude-module",
        "pygments",
        "--exclude-module",
        "setuptools",
        "--exclude-module",
        "pythonnet",
        "--exclude-module",
        "clr_loader",
        "--exclude-module",
        "dnfile",
        "--exclude-module",
        "multiprocessing",
        "--exclude-module",
        "asyncio",
        "--exclude-module",
        "concurrent",
        "--exclude-module",
        "xmlrpc",
        "--exclude-module",
        "http",
        "--exclude-module",
        "email",
        "--exclude-module",
        "urllib",
        "--exclude-module",
        "ftplib",
        "--exclude-module",
        "poplib",
        "--exclude-module",
        "imaplib",
        "--exclude-module",
        "smtplib",
        "run_trainer.py",
    ]
    print(f"Executing: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    print("\n[SUCCESS] Build complete! Executable located at: dist/HowToFishTrainer.exe")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build How to Fish Trainer executable")
    parser.add_argument(
        "--console",
        action="store_true",
        help="Build with visible console window instead of clean windowed GUI mode",
    )
    args = parser.parse_args()
    build(console=args.console)

