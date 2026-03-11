"""Простое окно для pyembed (windowed exe без консоли)."""
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from .config import add_recent_version, get_root
from .download import add_pip, fetch_versions, install_embeddable
from .local import get_version_dir, has_pip, list_installed, uninstall_version

if sys.platform == "win32":
    from .path_env import path_add


def _run_in_thread(root: tk.Tk, func: Callable[[], Any], on_done: Callable[[Any, Exception | None], None]) -> None:
    """Запуск func() в потоке; по завершении вызвать on_done(result, error)."""
    result: list[Any] = [None]
    error: list[Exception | None] = [None]

    def work() -> None:
        try:
            result[0] = func()
        except Exception as e:
            error[0] = e

    def schedule_done() -> None:
        on_done(result[0], error[0])

    thread = threading.Thread(target=work, daemon=True)
    thread.start()

    def poll() -> None:
        if thread.is_alive():
            root.after(200, poll)
        else:
            schedule_done()

    root.after(200, poll)


def run_gui() -> int:
    """Запуск главного окна (список версий, Install / Uninstall / Add pip / PATH)."""
    root_dir = get_root()

    root = tk.Tk()
    root.title("pyembed — Python Embeddable Manager")
    root.minsize(400, 300)
    root.geometry("500x400")

    # Заголовок и путь
    frame_top = ttk.Frame(root, padding=8)
    frame_top.pack(fill=tk.X)
    ttk.Label(frame_top, text="Python Embeddable Manager", font=("", 12, "bold")).pack(anchor=tk.W)
    ttk.Label(frame_top, text=f"Folder: {root_dir}", foreground="gray").pack(anchor=tk.W)

    # Список версий
    list_frame = ttk.LabelFrame(root, text="Installed versions", padding=4)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
    listbox = tk.Listbox(list_frame, height=10, font=("Consolas", 10))
    scroll = ttk.Scrollbar(list_frame)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scroll.set)
    scroll.config(command=listbox.yview)

    def refresh_list() -> None:
        listbox.delete(0, tk.END)
        for v in list_installed(root_dir):
            pip_mark = " [pip]" if has_pip(root_dir, v) else ""
            listbox.insert(tk.END, f"{v}{pip_mark}")

    def get_selected_version() -> str | None:
        sel = listbox.curselection()
        if not sel:
            return None
        text = listbox.get(sel[0])
        return text.split()[0] if text else None  # "3.12.0 [pip]" -> "3.12.0"

    # Кнопки
    btn_frame = ttk.Frame(root, padding=8)
    btn_frame.pack(fill=tk.X)

    def do_install() -> None:
        versions_available: list[str] = []
        try:
            versions_available = fetch_versions()[:30]
        except Exception:
            pass

        win = tk.Toplevel(root)
        win.title("Install version")
        win.transient(root)
        win.grab_set()
        ttk.Label(win, text="Version (e.g. 3.12.0):").pack(anchor=tk.W, padx=8, pady=4)
        ent = ttk.Entry(win, width=20)
        ent.pack(fill=tk.X, padx=8, pady=4)
        if versions_available:
            ent.insert(0, versions_available[0])
        var_pip = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text="Install pip", variable=var_pip).pack(anchor=tk.W, padx=8, pady=4)

        def ok() -> None:
            ver = ent.get().strip()
            win.destroy()
            if not ver:
                return
            win_work = tk.Toplevel(root)
            win_work.title("Installing...")
            ttk.Label(win_work, text=f"Installing {ver}...").pack(padx=20, pady=20)
            win_work.transient(root)
            win_work.grab_set()

            def task() -> None:
                install_embeddable(ver, root_dir, with_pip=var_pip.get(), progress=False)
                add_recent_version(root_dir, ver)

            def done(res: object, err: Exception | None) -> None:
                try:
                    win_work.destroy()
                except tk.TclError:
                    pass
                refresh_list()
                if err:
                    messagebox.showerror("Install failed", str(err))
                else:
                    messagebox.showinfo("Done", f"Installed {ver}.")

            _run_in_thread(root, task, done)

        ttk.Button(win, text="OK", command=ok).pack(side=tk.RIGHT, padx=8, pady=8)
        ttk.Button(win, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=4, pady=8)
        ent.focus_set()
        win.bind("<Return>", lambda e: ok())

    def do_uninstall() -> None:
        ver = get_selected_version()
        if not ver:
            messagebox.showinfo("Uninstall", "Select a version in the list.")
            return
        if not messagebox.askyesno("Uninstall", f"Remove {ver}?"):
            return

        def task() -> None:
            uninstall_version(root_dir, ver)

        def done(_res: object, err: Exception | None) -> None:
            refresh_list()
            if err:
                messagebox.showerror("Uninstall failed", str(err))
            else:
                messagebox.showinfo("Done", f"Removed {ver}.")

        _run_in_thread(root, task, done)

    def do_add_pip() -> None:
        ver = get_selected_version()
        if not ver:
            messagebox.showinfo("Add pip", "Select a version in the list.")
            return
        if has_pip(root_dir, ver):
            messagebox.showinfo("Add pip", f"{ver} already has pip.")
            return

        win_work = tk.Toplevel(root)
        win_work.title("Installing pip...")
        ttk.Label(win_work, text=f"Adding pip to {ver}...").pack(padx=20, pady=20)
        win_work.transient(root)
        win_work.grab_set()

        def task() -> None:
            add_pip(root_dir, ver, progress=False)

        def done(_res: object, err: Exception | None) -> None:
            try:
                win_work.destroy()
            except tk.TclError:
                pass
            refresh_list()
            if err:
                messagebox.showerror("Add pip failed", str(err))
            else:
                messagebox.showinfo("Done", f"pip installed for {ver}.")

        _run_in_thread(root, task, done)

    def do_path_add() -> None:
        if sys.platform != "win32":
            messagebox.showinfo("PATH", "PATH management is only on Windows.")
            return
        ver = get_selected_version()
        if not ver:
            messagebox.showinfo("Add to PATH", "Select a version in the list.")
            return
        dir_path = get_version_dir(root_dir, ver)
        try:
            if path_add(dir_path):
                messagebox.showinfo("PATH", f"Added {ver} to user PATH.\nNew consoles will see it.")
            else:
                messagebox.showinfo("PATH", "Already in PATH.")
        except Exception as e:
            messagebox.showerror("PATH", str(e))

    ttk.Button(btn_frame, text="Install...", command=do_install).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Uninstall", command=do_uninstall).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Add pip", command=do_add_pip).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Add to PATH", command=do_path_add).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Refresh", command=refresh_list).pack(side=tk.LEFT, padx=2)

    refresh_list()
    root.mainloop()
    return 0
