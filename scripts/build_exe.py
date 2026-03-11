#!/usr/bin/env python3
"""
Сборка одного exe через PyInstaller.
Запуск из корня проекта: python scripts/build_exe.py [--gui]
Требуется: pip install pyinstaller
--gui: без консоли (--windowed), имя pyembed-gui
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    gui = "--gui" in sys.argv
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
        "pyembed-gui" if gui else "pyembed",
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
        "--windowed" if gui else "--console",
        str(ROOT / "run.py"),
    ]
    if sys.platform == "win32":
        cmd.extend(["--hidden-import", "pyembed.path_env"])
    if gui:
        cmd.extend(["--hidden-import", "pyembed.gui"])
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
