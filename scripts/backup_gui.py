#!/usr/bin/env python3
"""
GUI для бэкапа исходников проекта (вызывает backup_sources.run_backup).
Только стандартная библиотека (tkinter). Запуск из корня: python scripts/backup_gui.py
"""
import os
import subprocess
import sys
import threading
from pathlib import Path

# чтобы импортировать backup_sources при запуске из корня или из scripts/
_scripts = Path(__file__).resolve().parent
_root = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:
    print("Требуется tkinter (обычно идёт с Python).")
    sys.exit(1)

from backup_sources import BACKUPS_DIR, run_backup  # noqa: E402


def run_in_thread(tk_root, func, on_done):
    """Запустить func() в потоке и по завершении вызвать on_done(result или exc)."""
    def work():
        try:
            result = func()
            tk_root.after(0, lambda: on_done(result, None))
        except Exception as exc:  # pylint: disable=broad-except
            tk_root.after(0, lambda ex=exc: on_done(None, ex))
    t = threading.Thread(target=work, daemon=True)
    t.start()


def open_folder(path: Path) -> None:
    path = path.resolve()
    if not path.is_dir():
        path = path.parent
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def main_gui() -> None:
    root = tk.Tk()
    root.title("Бэкап исходников pyembed")
    root.minsize(320, 140)
    root.resizable(True, True)

    main = ttk.Frame(root, padding=12)
    main.pack(fill=tk.BOTH, expand=True)

    status = tk.StringVar(value="Нажмите «Создать бэкап» для упаковки исходников в ZIP.")
    ttk.Label(main, textvariable=status, wraplength=360).pack(fill=tk.X, pady=(0, 10))

    def do_backup():
        status.set("Создаётся архив…")
        btn.state(["disabled"])

        def on_done(result, exc):
            btn.state(["!disabled"])
            if exc:
                status.set(f"Ошибка: {exc}")
                messagebox.showerror("Ошибка", str(exc))
                return
            path, count, size_mb = result
            status.set(f"Готово: {path.name}\nФайлов: {count}, размер: {size_mb:.2f} МБ")
            messagebox.showinfo("Бэкап создан", f"{path}\nФайлов: {count}, размер: {size_mb:.2f} МБ")

        run_in_thread(root, run_backup, on_done)

    btn = ttk.Button(main, text="Создать бэкап", command=do_backup)
    btn.pack(pady=4)

    def open_backups():
        BACKUPS_DIR.mkdir(exist_ok=True)
        open_folder(BACKUPS_DIR)

    ttk.Button(main, text="Открыть папку бэкапов", command=open_backups).pack(pady=4)

    root.mainloop()


if __name__ == "__main__":
    main_gui()
