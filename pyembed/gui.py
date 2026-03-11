"""
GUI для менеджера pyembed (установка, удаление, PATH, pip, doctor и т.д.).
Как в scripts/pyembed_gui.py: вызывает pyembed через subprocess (или тот же exe при frozen).
"""
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, ttk
except ImportError:
    raise SystemExit("Требуется tkinter (обычно идёт с Python).")

from .config import get_default_version, get_root, set_default_version
from .local import get_python_exe, list_installed
from .path_env import path_contains


def _project_root() -> Path:
    """Корень для cwd при запуске subprocess."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(get_root()).resolve().parent


def _pyembed_cmd(*args: str) -> list[str]:
    """Аргументы для запуска pyembed: при frozen — тот же exe, иначе python -m pyembed."""
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-u", "-m", "pyembed", *args]


def _run_cmd(
    tk_root: tk.Tk,
    args: list[str],
    log_callback: Callable[[str], None],
    done_callback: Callable[[int], None],
) -> None:
    """Запуск команды в потоке; вывод — в log_callback(line); по завершении — done_callback(returncode)."""
    def work() -> None:
        try:
            env = {
                **os.environ,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUNBUFFERED": "1",
            }
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(_project_root()),
                env=env,
                bufsize=0,
            )
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip("\r\n")
                if line:
                    tk_root.after(0, lambda ln=line: log_callback(ln))
            proc.wait()
            tk_root.after(0, lambda: done_callback(proc.returncode))
        except Exception as exc:
            tk_root.after(0, lambda ex=exc: log_callback(f"Ошибка: {ex}\n"))
            tk_root.after(0, lambda: done_callback(-1))
    t = threading.Thread(target=work, daemon=True)
    t.start()


def _refresh_list(listbox: tk.Listbox, root_dir: str) -> None:
    """Обновить список установленных версий в listbox."""
    default = get_default_version(root_dir)
    listbox.delete(0, tk.END)
    for v in list_installed(root_dir):
        label = v
        if v == default:
            label = f"{v} ★ (по умолчанию)"
        try:
            exe = get_python_exe(root_dir, v)
            if exe and path_contains(os.path.dirname(exe)):
                label += " [PATH]"
        except Exception:
            pass
        listbox.insert(tk.END, label)


def _get_selected_version(listbox: tk.Listbox) -> str | None:
    """Из выбранной строки listbox извлечь номер версии (без ★ и [PATH])."""
    sel = listbox.curselection()
    if not sel:
        return None
    text = listbox.get(sel[0])
    return text.split()[0] if text else None


def main_gui() -> None:
    """Главное окно: список версий, кнопки действий, лог вывода команд."""
    root = tk.Tk()
    root.title("pyembed — менеджер embeddable Python")
    root.minsize(420, 480)
    root.resizable(True, True)

    root_dir = get_root()

    main = ttk.Frame(root, padding=8)
    main.pack(fill=tk.BOTH, expand=True)

    left = ttk.Frame(main)
    left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
    ttk.Label(left, text="Установленные версии:", font=("TkDefaultFont", 9)).pack(anchor=tk.W)
    list_frame = ttk.Frame(left)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=4)
    scroll = ttk.Scrollbar(list_frame)
    listbox = tk.Listbox(list_frame, height=12, width=26, yscrollcommand=scroll.set, font=("TkDefaultFont", 10))
    scroll.config(command=listbox.yview)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    _refresh_list(listbox, root_dir)

    right = ttk.Frame(main)
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    ttk.Label(right, text=f"Корень: {root_dir}", font=("TkDefaultFont", 9)).pack(anchor=tk.W)
    status_var = tk.StringVar(value="Выберите версию в списке для действий с ней.")
    ttk.Label(right, textvariable=status_var, font=("TkDefaultFont", 9)).pack(anchor=tk.W, pady=(0, 6))

    all_buttons: list[ttk.Button] = []
    selection_buttons: list[ttk.Button] = []

    def add_btn(parent: ttk.Frame, text: str, cmd: Callable[[], None], need_selection: bool = False) -> ttk.Button:
        b = ttk.Button(parent, text=text, command=cmd)
        all_buttons.append(b)
        if need_selection:
            selection_buttons.append(b)
        return b

    def log(line: str) -> None:
        log_text.insert(tk.END, line + "\n")
        log_text.see(tk.END)

    def update_selection_buttons() -> None:
        has_sel = _get_selected_version(listbox) is not None
        for b in selection_buttons:
            b.state(["!disabled"] if has_sel else ["disabled"])

    def set_buttons_state(state: str) -> None:
        for b in all_buttons:
            b.state(["!disabled"] if state == "normal" else ["disabled"])
        if state == "normal":
            update_selection_buttons()

    def run_and_log(*args: str) -> None:
        set_buttons_state("disabled")
        status_var.set("Выполняется…")
        log(f"\n>>> pyembed {' '.join(args)}")
        def done(returncode: int) -> None:
            set_buttons_state("normal")
            status_var.set("Готово." if returncode == 0 else f"Команда завершилась с кодом {returncode}.")
            _refresh_list(listbox, root_dir)
            log(f"[код выхода: {returncode}]\n")
        _run_cmd(root, _pyembed_cmd(*args), log, done)

    def on_install() -> None:
        version = simpledialog.askstring("Установить", "Версия (например 3.12.0):", parent=root)
        if not version or not version.strip():
            return
        version = version.strip()
        with_pip = messagebox.askyesno("pip", "Установить pip в эту версию?", parent=root)
        args = ["install", version, "-y"]
        if with_pip:
            args.append("--pip")
        run_and_log(*args)

    def on_uninstall() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("Удаление", "Выберите версию в списке.", parent=root)
            return
        if not messagebox.askyesno("Удалить", f"Удалить версию {ver}?", parent=root):
            return
        run_and_log("uninstall", ver, "-y")

    def on_default() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("По умолчанию", "Выберите версию в списке.", parent=root)
            return
        try:
            set_default_version(root_dir, ver)
            _refresh_list(listbox, root_dir)
            log(f"Версия по умолчанию: {ver}\n")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=root)

    def on_path_add() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("PATH", "Выберите версию в списке.", parent=root)
            return
        run_and_log("path", "add", ver)

    def on_path_remove() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("PATH", "Выберите версию в списке.", parent=root)
            return
        run_and_log("path", "remove", ver)

    def on_path_fix_duplicates() -> None:
        run_and_log("path", "fix-duplicates")

    def on_pip() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("pip", "Выберите версию в списке.", parent=root)
            return
        run_and_log("pip", ver, "list")

    def on_add_pip() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("add-pip", "Выберите версию в списке.", parent=root)
            return
        run_and_log("add-pip", ver)

    def on_upgrade_pip() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("upgrade-pip", "Выберите версию в списке.", parent=root)
            return
        run_and_log("upgrade-pip", ver)

    def on_venv() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("venv", "Выберите версию в списке.", parent=root)
            return
        name = simpledialog.askstring("venv", "Имя каталога окружения (.venv):", initialvalue=".venv", parent=root)
        if name is None:
            return
        run_and_log("venv", ver, name or ".venv")

    def on_packages() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("Пакеты", "Выберите версию в списке.", parent=root)
            return
        run_and_log("packages", ver, "list")

    def on_cache_list() -> None:
        run_and_log("cache", "list")

    def on_cache_clear() -> None:
        if not messagebox.askyesno("Кэш", "Очистить весь кэш?", parent=root):
            return
        run_and_log("cache", "clear")

    def on_info() -> None:
        ver = _get_selected_version(listbox)
        if ver:
            run_and_log("info", ver)
        else:
            run_and_log("info")

    def on_doctor() -> None:
        run_and_log("doctor")

    def on_ide() -> None:
        ver = _get_selected_version(listbox)
        if ver:
            run_and_log("ide", ver)
        else:
            run_and_log("ide")

    def on_refresh() -> None:
        _refresh_list(listbox, root_dir)
        update_selection_buttons()
        log("Список обновлён.\n")

    def on_available() -> None:
        run_and_log("list", "-a")

    def on_copy_to_folder() -> None:
        ver = _get_selected_version(listbox)
        if not ver:
            messagebox.showinfo("Копирование", "Выберите версию в списке.", parent=root)
            return
        default_dest = os.path.join("C:", "Python", ver)
        dest = simpledialog.askstring(
            "Копировать в папку",
            "Папка назначения (будет добавлена в PATH):",
            initialvalue=default_dest,
            parent=root,
        )
        if not dest:
            return
        run_and_log("copy", ver, dest.strip())

    groups_frame = ttk.Frame(right)
    groups_frame.pack(fill=tk.X, pady=4)

    g_ver = ttk.LabelFrame(groups_frame, text=" Версии ", padding=4)
    g_ver.pack(side=tk.TOP, fill=tk.X, pady=2)
    add_btn(g_ver, "Установить", on_install).pack(side=tk.LEFT, padx=2)
    add_btn(g_ver, "Удалить", on_uninstall, need_selection=True).pack(side=tk.LEFT, padx=2)
    add_btn(g_ver, "По умолчанию", on_default, need_selection=True).pack(side=tk.LEFT, padx=2)
    add_btn(g_ver, "Обновить", on_refresh).pack(side=tk.LEFT, padx=2)
    add_btn(g_ver, "Доступные версии", on_available).pack(side=tk.LEFT, padx=2)
    add_btn(g_ver, "Копировать в папку", on_copy_to_folder, need_selection=True).pack(side=tk.LEFT, padx=2)

    g_path = ttk.LabelFrame(groups_frame, text=" PATH ", padding=4)
    g_path.pack(side=tk.TOP, fill=tk.X, pady=2)
    add_btn(g_path, "В PATH", on_path_add, need_selection=True).pack(side=tk.LEFT, padx=2)
    add_btn(g_path, "Убрать из PATH", on_path_remove, need_selection=True).pack(side=tk.LEFT, padx=2)
    add_btn(g_path, "Убрать дубликаты", on_path_fix_duplicates).pack(side=tk.LEFT, padx=2)

    g_pip = ttk.LabelFrame(groups_frame, text=" pip ", padding=4)
    g_pip.pack(side=tk.TOP, fill=tk.X, pady=2)
    add_btn(g_pip, "pip list", on_pip, need_selection=True).pack(side=tk.LEFT, padx=2)
    add_btn(g_pip, "add-pip", on_add_pip, need_selection=True).pack(side=tk.LEFT, padx=2)
    add_btn(g_pip, "upgrade-pip", on_upgrade_pip, need_selection=True).pack(side=tk.LEFT, padx=2)

    g_env = ttk.LabelFrame(groups_frame, text=" Окружение ", padding=4)
    g_env.pack(side=tk.TOP, fill=tk.X, pady=2)
    add_btn(g_env, "venv", on_venv, need_selection=True).pack(side=tk.LEFT, padx=2)
    add_btn(g_env, "Пакеты", on_packages, need_selection=True).pack(side=tk.LEFT, padx=2)

    g_cache = ttk.LabelFrame(groups_frame, text=" Кэш ", padding=4)
    g_cache.pack(side=tk.TOP, fill=tk.X, pady=2)
    add_btn(g_cache, "Показать кэш", on_cache_list).pack(side=tk.LEFT, padx=2)
    add_btn(g_cache, "Очистить кэш", on_cache_clear).pack(side=tk.LEFT, padx=2)

    g_help = ttk.LabelFrame(groups_frame, text=" Справка ", padding=4)
    g_help.pack(side=tk.TOP, fill=tk.X, pady=2)
    add_btn(g_help, "Инфо", on_info).pack(side=tk.LEFT, padx=2)
    add_btn(g_help, "Doctor", on_doctor).pack(side=tk.LEFT, padx=2)
    add_btn(g_help, "IDE (путь)", on_ide, need_selection=True).pack(side=tk.LEFT, padx=2)

    listbox.bind("<<ListboxSelect>>", lambda e: update_selection_buttons())
    update_selection_buttons()

    ttk.Label(right, text="Вывод команд:").pack(anchor=tk.W, pady=(8, 0))
    log_frame = ttk.Frame(right, padding=0)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=4)
    log_scroll = ttk.Scrollbar(log_frame)
    log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, yscrollcommand=log_scroll.set, font=("Consolas", 9))
    log_scroll.config(command=log_text.yview)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def copy_log_selection() -> None:
        try:
            text = log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            text = log_text.get("1.0", tk.END)
        if text.strip():
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update_idletasks()

    def on_copy(_e: tk.Event) -> str:
        copy_log_selection()
        return "break"

    log_text.bind("<Control-c>", on_copy)
    log_text.bind("<Control-C>", on_copy)
    log_context = tk.Menu(log_text, tearoff=0)
    log_context.add_command(label="Копировать", command=copy_log_selection)

    def show_log_context(e: tk.Event) -> None:
        try:
            log_context.tk_popup(e.x_root, e.y_root)
        finally:
            log_context.grab_release()

    log_text.bind("<Button-3>", show_log_context)

    root.mainloop()


def run_gui() -> int:
    """Точка входа при запуске windowed exe без аргументов."""
    main_gui()
    return 0
