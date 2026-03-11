#!/usr/bin/env python3
"""
GUI для менеджера pyembed. Запуск из корня проекта: python scripts/pyembed_gui.py
Реализация в pyembed.gui (то же окно открывается при запуске pyembed-gui.exe без аргументов).
"""
import sys
from pathlib import Path

# Корень проекта для запуска из scripts/
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pyembed.gui import main_gui

if __name__ == "__main__":
    main_gui()
