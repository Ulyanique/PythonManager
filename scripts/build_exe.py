#!/usr/bin/env python3
"""
Сборка одного exe через PyInstaller.
Запуск из корня проекта: python scripts/build_exe.py
Требуется: pip install pyinstaller
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Установите PyInstaller: pip install pyinstaller", file=sys.stderr)
        return 1
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        "pyembed",
        "--paths",
        str(ROOT),
        "--hidden-import",
        "pyembed",
        "--hidden-import",
        "pyembed.cli",
        "--hidden-import",
        "pyembed.config",
        "--hidden-import",
        "pyembed.download",
        "--hidden-import",
        "pyembed.local",
        "--hidden-import",
        "pyembed.version_util",
        "--console",
        str(ROOT / "run.py"),
    ]
    if sys.platform == "win32":
        cmd.extend(["--hidden-import", "pyembed.path_env"])
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
