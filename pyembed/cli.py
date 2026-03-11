"""CLI для менеджера embeddable Python."""
import argparse
import os
import shutil
import subprocess
import sys
from collections import Counter

from .config import (
    add_recent_version,
    get_default_version,
    get_recent_versions,
    get_root,
    set_default_version,
)
from .download import (
    NetworkError,
    add_pip,
    clear_cache,
    fetch_versions,
    install_embeddable,
    list_cache,
)
from .local import (
    copy_version_to,
    get_python_exe,
    get_version_dir_size,
    has_pip,
    list_installed,
    uninstall_version,
    verify_version,
)


def _suggest_versions(version: str, limit: int = 5) -> list[str]:
    """При 404: версии с python.org для подсказки «возможно, вы имели в виду»."""
    try:
        available = fetch_versions()
        return available[:limit] if available else []
    except Exception:
        return []


def _whatsnew_url(version: str) -> str:
    """Ссылка на What's New для данной версии (major.minor)."""
    parts = version.split(".")
    if len(parts) >= 2:
        return f"https://docs.python.org/3/whatsnew/{parts[0]}.{parts[1]}.html"
    return "https://docs.python.org/3/whatsnew/"


def _show_no_console_message() -> None:
    """Показать сообщение при запуске windowed exe без аргументов (нет консоли)."""
    msg = (
        "This is the windowed build (no console).\n\n"
        "Run from Command Prompt or a shortcut with a command, e.g.:\n"
        "  pyembed-gui.exe list\n"
        "  pyembed-gui.exe install 3.12.0 --pip"
    )
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
                None, msg, "pyembed", 0x40
            )
        except Exception:
            pass
    if sys.stderr and not getattr(sys.stderr, "closed", True):
        print(msg, file=sys.stderr)


def _copy_to_clipboard(text: str) -> bool:
    """Скопировать текст в буфер обмена (Windows). Возвращает True при успехе."""
    if sys.platform != "win32":
        return False
    try:
        env = {**os.environ, "PYEMBED_CLIP": text}
        r = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "[System.Environment]::GetEnvironmentVariable('PYEMBED_CLIP', 'Process') | Set-Clipboard",
            ],
            env=env,
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def _resolve_version(root: str, version: str | None, for_what: str = "команда") -> str | None:
    """Если version не задана, подставляем версию по умолчанию. Иначе None и сообщение в stderr."""
    if version:
        return version
    default = get_default_version(root)
    if default and get_python_exe(root, default):
        return default
    if default:
        print(
            f"Версия по умолчанию ({default}) не найдена. Задайте заново: pyembed default <версия>",
            file=sys.stderr,
        )
    else:
        print(
            "Укажите версию или задайте по умолчанию: pyembed default 3.12.0",
            file=sys.stderr,
        )
    return None


def _print_error(e: Exception, hint: str = "") -> None:
    """Печатает ошибку и опциональную подсказку в stderr."""
    print(f"Ошибка: {e}", file=sys.stderr)
    if hint:
        print(f"  → {hint}", file=sys.stderr)


def cmd_list(args: argparse.Namespace) -> int:
    root = get_root()
    if args.available:
        print("Доступные версии (python.org/ftp):")
        for v in fetch_versions():
            print(f"  {v}")
        return 0
    print(f"Установленные версии (корень: {root}):")
    installed = list_installed(root)
    if not installed:
        print("  (нет установленных версий)")
        return 0
    for v in installed:
        print(f"  {v}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    root = get_root()
    dry_run = getattr(args, "dry_run", False)
    try:
        path = install_embeddable(
            args.version,
            root,
            arch=args.arch,
            with_pip=args.pip,
            progress=True,
            dry_run=dry_run,
        )
        if dry_run:
            return 0
        resolved_version = os.path.basename(path)
        if resolved_version != args.version.strip():
            print(f"Установлена версия {resolved_version} (указано: {args.version}).", flush=True)
        print(f"Готово: {path}", flush=True)
        if not getattr(args, "yes", False):
            print(f"Добавить в PATH: pyembed path add {resolved_version}")
            print(f"Что нового: {_whatsnew_url(resolved_version)}")
        return 0
    except FileNotFoundError as e:
        _print_error(e, "Проверьте доступные версии: pyembed list -a")
        suggestions = _suggest_versions(args.version)
        if suggestions:
            print(f"  Возможно, вы имели в виду: {', '.join(suggestions[:5])}", file=sys.stderr)
        return 1
    except NetworkError as e:
        _print_error(e, e.hint)
        return 1
    except OSError as e:
        _print_error(e, "Проверьте права на запись в папку с версиями.")
        return 1
    except Exception as e:
        _print_error(e)
        return 1


def cmd_default(args: argparse.Namespace) -> int:
    """Показать или задать версию по умолчанию."""
    root = get_root()
    if getattr(args, "version", None):
        version = args.version
        if not get_python_exe(root, version):
            print(f"Версия {version} не установлена. Сначала: pyembed install {version}", file=sys.stderr)
            return 1
        set_default_version(root, version)
        print(f"Версия по умолчанию: {version}")
    else:
        v = get_default_version(root)
        if v:
            print(v)
        else:
            print("Версия по умолчанию не задана. Задайте: pyembed default 3.12.0")
    return 0


def cmd_path_show(args: argparse.Namespace) -> int:
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "path show")
    if not version:
        return 1
    exe = get_python_exe(root, version)
    if not exe:
        print(
            f"Версия {version} не установлена. Установите: pyembed install {version}",
            file=sys.stderr,
        )
        return 1
    print(exe)
    if getattr(args, "copy", False) and _copy_to_clipboard(exe):
        print("Путь скопирован в буфер обмена.", file=sys.stderr)
    return 0


def cmd_which(args: argparse.Namespace) -> int:
    """Вывести полный путь к python.exe для версии (или default). Удобно для скриптов и CI."""
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "which")
    if not version:
        return 1
    exe = get_python_exe(root, version)
    if not exe:
        print(
            f"Версия {version} не установлена. Установите: pyembed install {version}",
            file=sys.stderr,
        )
        return 1
    print(exe)
    if getattr(args, "copy", False) and _copy_to_clipboard(exe):
        print("Путь скопирован в буфер обмена.", file=sys.stderr)
    return 0


def cmd_path_add(args: argparse.Namespace) -> int:
    if sys.platform != "win32":
        print("path add/remove поддерживаются только на Windows.", file=sys.stderr)
        return 1
    from .path_env import path_add

    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(
            f"Версия {args.version} не установлена. Установите: pyembed install {args.version}",
            file=sys.stderr,
        )
        return 1
    dir_path = os.path.dirname(exe)
    try:
        if path_add(dir_path):
            print(f"Добавлено в PATH: {dir_path}")
            print("Изменения вступят в силу в новых окнах консоли.")
        else:
            print(f"Путь уже в PATH: {dir_path}")
        return 0
    except Exception as e:
        _print_error(e)
        return 1


def cmd_path_remove(args: argparse.Namespace) -> int:
    if sys.platform != "win32":
        print("path add/remove поддерживаются только на Windows.", file=sys.stderr)
        return 1
    from .path_env import path_remove

    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(
            f"Версия {args.version} не установлена.",
            file=sys.stderr,
        )
        return 1
    dir_path = os.path.dirname(exe)
    try:
        if path_remove(dir_path):
            print(f"Удалено из PATH: {dir_path}")
            print("Изменения вступят в силу в новых окнах консоли.")
        else:
            print(f"Пути не было в PATH: {dir_path}")
        return 0
    except Exception as e:
        _print_error(e)
        return 1


def cmd_path_list(args: argparse.Namespace) -> int:
    if sys.platform != "win32":
        print("path list поддерживается только на Windows.", file=sys.stderr)
        return 1
    from .path_env import get_user_path_entries

    root = get_root()
    root_norm = os.path.normpath(os.path.abspath(root))
    installed = list_installed(root)
    try:
        entries = get_user_path_entries()
    except Exception as e:
        _print_error(e)
        return 1
    in_path = [
        (v, os.path.normpath(os.path.join(root_norm, v)))
        for v in installed
        if os.path.normpath(os.path.join(root_norm, v)) in entries
    ]
    if not in_path:
        print("В PATH пользователя нет версий из этой папки.")
        return 0
    print("В PATH пользователя (из этого корня):")
    for ver, path in in_path:
        print(f"  {ver}  {path}")
    return 0


def cmd_path_fix_duplicates(args: argparse.Namespace) -> int:
    """Удалить дубликаты записей в PATH пользователя (Windows)."""
    if sys.platform != "win32":
        print("path fix-duplicates поддерживается только на Windows.", file=sys.stderr)
        return 1
    from .path_env import path_remove_duplicates
    try:
        n = path_remove_duplicates()
        if n > 0:
            print(f"Удалено дубликатов в PATH: {n}. Изменения в новых окнах консоли.")
        else:
            print("Дубликатов в PATH нет.")
        return 0
    except Exception as e:
        _print_error(e)
        return 1


def cmd_copy(args: argparse.Namespace) -> int:
    """Скопировать версию в папку (например C:/Python/3.15) и опционально добавить в PATH."""
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "copy")
    if not version:
        return 1
    dest = getattr(args, "dest", None)
    if not dest:
        dest = os.path.join("C:", "Python", version)
    force = getattr(args, "force", False)
    no_path = getattr(args, "no_path", False)
    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        dest_abs = os.path.normpath(os.path.abspath(dest))
        print(f"[dry-run] Будет скопировано: {version} → {dest_abs}")
        if sys.platform == "win32" and not no_path:
            print(f"[dry-run] Будет добавлено в PATH: {dest_abs}")
        return 0
    try:
        print(f"Копирование {version} в {dest}...", flush=True)
        dest_abs = copy_version_to(root, version, dest, force=force)
        print(f"Скопировано: {version} → {dest_abs}")
        if sys.platform == "win32" and not no_path:
            from .path_env import path_add
            if path_add(dest_abs):
                print(f"Добавлено в PATH: {dest_abs}")
                print("Изменения вступят в силу в новых окнах консоли.")
            else:
                print(f"Путь уже в PATH: {dest_abs}")
        return 0
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        _print_error(e)
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    """Проверить целостность установленной версии (python.exe и ключевые файлы)."""
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "verify")
    if not version:
        return 1
    ok, missing = verify_version(root, version)
    if ok:
        print(f"{version}: всё на месте.")
        return 0
    print(f"{version}: не найдено: {', '.join(missing)}", file=sys.stderr)
    return 1


def cmd_cache_list(args: argparse.Namespace) -> int:
    """Показать файлы в кэше."""
    root = get_root()
    items = list_cache(root)
    if not items:
        print("Кэш пуст.")
        return 0
    print(f"Кэш ({root}/.cache):")
    for name, size in items:
        mb = size / (1024 * 1024)
        print(f"  {name}  {mb:.1f} МБ")
    return 0


def cmd_cache_clear(args: argparse.Namespace) -> int:
    """Очистить кэш (все или указанной версии)."""
    root = get_root()
    version = getattr(args, "version", None)
    n = clear_cache(root, version)
    if version:
        print(f"Удалено файлов в кэше для {version}: {n}")
    else:
        print(f"Удалено файлов в кэше: {n}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Информация о версии: путь, pip, размер, в PATH."""
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "info")
    if not version:
        return 1
    exe = get_python_exe(root, version)
    if not exe:
        print(f"Версия {version} не установлена.", file=sys.stderr)
        return 1
    dir_path = os.path.dirname(exe)
    size_mb = get_version_dir_size(root, version) / (1024 * 1024)
    in_path = ""
    if sys.platform == "win32":
        try:
            from .path_env import path_contains
            in_path = " да" if path_contains(dir_path) else " нет"
        except Exception:
            in_path = " ?"
    print(f"Версия:    {version}")
    print(f"Путь:      {dir_path}")
    print(f"pip:       {'да' if has_pip(root, version) else 'нет'}")
    print(f"Размер:    {size_mb:.1f} МБ")
    if in_path:
        print(f"В PATH:    {in_path.strip()}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Проверка: python.org, место на диске, целостность установок, PATH (Windows)."""
    root = get_root()
    print(f"Проверка (корень: {root})")
    issues: list[str] = []
    # Сеть
    try:
        fetch_versions()
        print("  python.org: доступен")
    except Exception as e:
        issues.append(f"python.org: {e!s}")
        print(f"  python.org: недоступен — {e}", file=sys.stderr)
    # Место на диске
    try:
        usage = shutil.disk_usage(os.path.abspath(root))
        free_mb = usage.free // (1024 * 1024)
        print(f"  Место на диске: свободно {free_mb} МБ")
        if free_mb < 500:
            issues.append("Мало места на диске (<500 МБ)")
    except Exception as e:
        issues.append(f"Диск: {e!s}")
    # Целостность установленных версий
    installed = list_installed(root)
    for ver in installed:
        ok, missing = verify_version(root, ver)
        if ok:
            print(f"  {ver}: OK")
        else:
            print(f"  {ver}: не хватает {missing}", file=sys.stderr)
            issues.append(f"{ver}: отсутствует {', '.join(missing)}")
    # Windows: дубликаты и несуществующие каталоги в PATH
    if sys.platform == "win32":
        try:
            from .path_env import (
                get_user_path_entries,
                path_list_missing,
                path_remove_duplicates,
                path_remove_missing,
            )
            entries = get_user_path_entries()
            counts = Counter(entries)
            dups = [e for e, c in counts.items() if c > 1]
            if dups:
                issues.append(f"Дубликаты в PATH: {len(dups)} записей")
                print(f"  PATH: дубликатов записей: {len(dups)}", file=sys.stderr)
                if getattr(args, "fix", False):
                    n = path_remove_duplicates()
                    print(f"  PATH: исправлено, удалено дубликатов: {n}")
                    issues.remove(f"Дубликаты в PATH: {len(dups)} записей")
                else:
                    print("  Исправить: pyembed path fix-duplicates или doctor --fix", file=sys.stderr)
            else:
                print("  PATH: дубликатов нет")
            missing_paths = path_list_missing()
            if missing_paths:
                issues.append(f"PATH: несуществующие каталоги: {len(missing_paths)}")
                print(f"  PATH: несуществующие каталоги: {len(missing_paths)}", file=sys.stderr)
                for p in missing_paths[:5]:
                    print(f"    - {p}", file=sys.stderr)
                if len(missing_paths) > 5:
                    print(f"    ... и ещё {len(missing_paths) - 5}", file=sys.stderr)
                if getattr(args, "fix", False):
                    removed = path_remove_missing()
                    print(f"  PATH: удалено несуществующих записей: {len(removed)}")
                    issues.remove(f"PATH: несуществующие каталоги: {len(missing_paths)}")
                else:
                    print("  Исправить: doctor --fix", file=sys.stderr)
        except Exception as e:
            print(f"  PATH: не удалось проверить — {e}", file=sys.stderr)
    if issues:
        print("\nОбнаружено проблем:", len(issues), file=sys.stderr)
        for i in issues:
            print(f"  - {i}", file=sys.stderr)
        return 1
    print("\nВсё в порядке.")
    return 0


def cmd_ide(args: argparse.Namespace) -> int:
    """Путь к интерпретатору и подсказка для Cursor/VS Code."""
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "ide")
    if not version:
        return 1
    exe = get_python_exe(root, version)
    if not exe:
        print(
            f"Версия {version} не установлена. Установите: pyembed install {version}",
            file=sys.stderr,
        )
        return 1
    if getattr(args, "json", False):
        import json
        print(json.dumps({"python.defaultInterpreterPath": exe}, ensure_ascii=False))
        return 0
    print(exe)
    print("Для Cursor / VS Code: укажите этот путь в python.defaultInterpreterPath")
    print("  (Ctrl+Shift+P → Python: Select Interpreter или в .vscode/settings.json)")
    print("  Или: pyembed ide --json для вставки в settings.json")
    return 0


def cmd_upgrade_pip(args: argparse.Namespace) -> int:
    """Обновить pip в установленной версии."""
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "upgrade-pip")
    if not version:
        return 1
    exe = get_python_exe(root, version)
    if not exe:
        print(f"Версия {version} не установлена.", file=sys.stderr)
        return 1
    if not has_pip(root, version):
        print(f"В {version} нет pip. Установите: pyembed add-pip {version}", file=sys.stderr)
        return 1
    return subprocess.call([exe, "-m", "pip", "install", "--upgrade", "pip"])


def cmd_run(args: argparse.Namespace) -> int:
    root = get_root()
    version = _resolve_version(root, getattr(args, "version", None), "run")
    if not version:
        return 1
    exe = get_python_exe(root, version)
    if not exe:
        print(f"Версия {version} не установлена. Установите: pyembed install {version}", file=sys.stderr)
        return 1
    cmd = [exe] + args.rest
    return subprocess.call(cmd)


def cmd_use(args: argparse.Namespace) -> int:
    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(f"Версия {args.version} не установлена. Установите: pyembed install {args.version}", file=sys.stderr)
        return 1
    dir_path = os.path.dirname(exe)
    print("Добавьте в PATH для использования этой версии:")
    print(f"  set PATH={dir_path};%PATH%")
    print(f"Или запускайте напрямую: {exe}")
    if getattr(args, "copy", False) and _copy_to_clipboard(dir_path):
        print("Путь скопирован в буфер обмена.", file=sys.stderr)
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    root = get_root()
    if not get_python_exe(root, args.version):
        print(f"Версия {args.version} не установлена.", file=sys.stderr)
        return 1
    if not getattr(args, "force", False):
        size_mb = get_version_dir_size(root, args.version) // (1024 * 1024)
        print(f"Освободится ~{size_mb} МБ.")
        confirm = input(f"Удалить {args.version}? (y/n): ").strip().lower()
        if confirm not in ("y", "yes", "д", "да"):
            return 0
    try:
        uninstall_version(root, args.version)
        print(f"Удалено: {args.version}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


def cmd_pip(args: argparse.Namespace) -> int:
    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(f"Версия {args.version} не установлена. Установите: pyembed install {args.version}", file=sys.stderr)
        return 1
    if not has_pip(root, args.version):
        print(
            f"В версии {args.version} нет pip. Установите заново с флагом --pip:\n"
            f"  pyembed install {args.version} --pip",
            file=sys.stderr,
        )
        return 1
    cmd = [exe, "-m", "pip"] + args.pip_args
    return subprocess.call(cmd)


def cmd_packages_list(args: argparse.Namespace) -> int:
    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(
            f"Версия {args.version} не установлена. Установите: pyembed install {args.version}",
            file=sys.stderr,
        )
        return 1
    if not has_pip(root, args.version):
        print(
            f"В {args.version} нет pip. Установите: pyembed add-pip {args.version}",
            file=sys.stderr,
        )
        return 1
    return subprocess.call([exe, "-m", "pip", "list"])


def cmd_packages_add(args: argparse.Namespace) -> int:
    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(
            f"Версия {args.version} не установлена. Установите: pyembed install {args.version}",
            file=sys.stderr,
        )
        return 1
    if not has_pip(root, args.version):
        print(
            f"В {args.version} нет pip. Установите: pyembed add-pip {args.version}",
            file=sys.stderr,
        )
        return 1
    if not args.packages:
        print("Укажите пакеты: pyembed packages <version> add requests ...", file=sys.stderr)
        return 1
    return subprocess.call([exe, "-m", "pip", "install"] + args.packages)


def cmd_packages_remove(args: argparse.Namespace) -> int:
    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(
            f"Версия {args.version} не установлена.",
            file=sys.stderr,
        )
        return 1
    if not has_pip(root, args.version):
        print(
            f"В {args.version} нет pip.",
            file=sys.stderr,
        )
        return 1
    if not args.packages:
        print("Укажите пакеты: pyembed packages <version> remove requests ...", file=sys.stderr)
        return 1
    return subprocess.call([exe, "-m", "pip", "uninstall", "-y"] + args.packages)


def cmd_add_pip(args: argparse.Namespace) -> int:
    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(
            f"Версия {args.version} не установлена. Установите: pyembed install {args.version}",
            file=sys.stderr,
        )
        return 1
    if has_pip(root, args.version):
        print(f"В {args.version} уже установлен pip.", file=sys.stderr)
        return 0
    try:
        add_pip(root, args.version, progress=True)
        print(f"pip установлен в {args.version}.")
        return 0
    except NetworkError as e:
        _print_error(e, e.hint)
        return 1
    except OSError as e:
        _print_error(e, "Проверьте права на запись в папку версии.")
        return 1
    except Exception as e:
        _print_error(e)
        return 1


def _run_venv(exe: str, path: str, version: str, root: str | None = None) -> tuple[int, bool]:
    """
    Запуск python -m venv. При отсутствии модуля venv и наличии pip пробует virtualenv.
    root — корень установок (для проверки has_pip и fallback на virtualenv).
    Возвращает (код выхода, использован_ли virtualenv).
    """
    result = subprocess.run(
        [exe, "-m", "venv", path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return (0, False)
    err = (result.stderr or "").strip()
    if "venv" in err or "No module named" in err:
        if root and has_pip(root, version):
            print("  Модуль venv недоступен. Пробуем virtualenv через pip...")
            subprocess.run(
                [exe, "-m", "pip", "install", "virtualenv", "-q"],
                capture_output=True,
                timeout=120,
            )
            r2 = subprocess.run(
                [exe, "-m", "virtualenv", path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r2.returncode == 0:
                return (0, True)
            if r2.stderr:
                print(r2.stderr.strip(), file=sys.stderr)
            return (r2.returncode, False)
        print(
            f"В embeddable-сборке {version} нет модуля venv.",
            "Установите pip (п. 4) и повторите — тогда будет использован virtualenv.",
            "Или используйте полную установку Python.",
            sep=" ",
            file=sys.stderr,
        )
    else:
        print(err, file=sys.stderr)
    return (result.returncode, False)


def cmd_venv(args: argparse.Namespace) -> int:
    """Создать venv от выбранной embeddable-версии."""
    root = get_root()
    exe = get_python_exe(root, args.version)
    if not exe:
        print(
            f"Версия {args.version} не установлена. Установите: pyembed install {args.version}",
            file=sys.stderr,
        )
        return 1
    name = args.name or ".venv"
    path = os.path.abspath(name)
    if os.path.exists(path):
        print(f"Каталог уже существует: {path}", file=sys.stderr)
        return 1
    rc, used_virtualenv = _run_venv(exe, path, args.version, root)
    if rc == 0:
        suffix = " (через virtualenv)" if used_virtualenv else ""
        print(f"Окружение создано{suffix}: {path}")
        print(f"Активация (Windows): {name}\\Scripts\\activate")
    return rc


def _print_installed(root: str) -> None:
    installed = list_installed(root)
    if not installed:
        print("  (нет установленных версий)")
        return
    for v in installed:
        pip_mark = " [pip]" if has_pip(root, v) else ""
        print(f"  {v}{pip_mark}")


def _choose_version_by_number(
    root: str, prompt: str = "Номер или версия (Enter — отмена): "
) -> str | None:
    """Выбор версии по номеру из списка или по строке (3.12.0)."""
    installed = list_installed(root)
    if not installed:
        print("Сначала установите хотя бы одну версию (меню → Скачать).")
        return None
    for i, v in enumerate(installed, 1):
        pip_mark = " [pip]" if has_pip(root, v) else ""
        print(f"  {i}. {v}{pip_mark}")
    recent = get_recent_versions(root)
    if recent:
        print(f"  Недавно: {', '.join(recent)}")
    raw = input(prompt).strip()
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(installed):
            return installed[idx - 1]
        print("Нет такого номера.")
        return None
    if get_python_exe(root, raw):
        return raw
    print(f"Версия {raw} не найдена.")
    return None


def _warn_encoding_if_needed() -> None:
    """Один раз предупреждает, если консоль не в UTF-8 (русский может отображаться криво)."""
    try:
        enc = (getattr(sys.stdout, "encoding") or "").lower()
        if enc in ("utf-8", "utf8", "cp65001", "utf-16"):
            return
        if sys.platform == "win32" and enc:
            print(
                "Подсказка: для корректного отображения русского выполните: chcp 65001",
                file=sys.stderr,
            )
    except Exception:
        pass


def run_interactive() -> int:
    """Интерактивное меню: не закрывается, предлагает скачать/удалить/pip."""
    _warn_encoding_if_needed()
    root = get_root()
    print("Python Embeddable Manager")
    print(f"Папка версий: {root}")
    print()

    while True:
        print("--- Установленные версии ---")
        _print_installed(root)
        print()
        print("  1 — Скачать версию (install)")
        print("  2 — Удалить версию")
        print("  3 — Pip (команда pip для версии)")
        print("  4 — Установить pip в версию")
        print("  5 — Пакеты (список / установить / удалить)")
        print("  6 — Создать venv (виртуальное окружение)")
        print("  7 — PATH: добавить/убрать версию или убрать дубликаты")
        print("  8 — Инфо о версии (путь, pip, размер, PATH)")
        print("  9 — Кэш (список / очистка)")
        print(" 10 — Обновить pip в версии")
        print(" 11 — Копировать версию в папку (C:/Python/3.15) и в PATH")
        print(" 12 — Выход")
        print()
        try:
            choice = input("Выбор (1-12): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        except RuntimeError as e:
            if "stdin" in str(e).lower():
                _show_no_console_message()
                return 1
            raise

        if not choice:
            continue
        if choice == "12":
            return 0
        if choice == "11":
            ver = _choose_version_by_number(root, "Какую версию скопировать? ")
            if ver:
                default_dest = os.path.join("C:", "Python", ver)
                dest = input(f"Папка назначения [{default_dest}]: ").strip() or default_dest
                force = input("Перезаписать, если папка существует? (y/n) [n]: ").strip().lower() in ("y", "yes", "д", "да")
                try:
                    dest_abs = copy_version_to(root, ver, dest, force=force)
                    print(f"Скопировано: {ver} → {dest_abs}")
                    if sys.platform == "win32":
                        from .path_env import path_add
                        if path_add(dest_abs):
                            print("Добавлено в PATH. Изменения в новых окнах консоли.")
                        else:
                            print("Путь уже в PATH.")
                except FileExistsError as e:
                    print(str(e), file=sys.stderr)
                except Exception as e:
                    _print_error(e)
            print()
            continue
        if choice == "1":
            print("\nДоступные версии (python.org, последние 50):")
            try:
                available = fetch_versions()
                for i, v in enumerate(available[:50], 1):
                    print(f"  {v}", end="\n" if i % 10 == 0 else "  ")
                if len(available) > 50:
                    print(f"\n  ... и ещё {len(available) - 50} (полный список: pyembed list -a)")
                elif available and len(available) % 10 != 0:
                    print()
            except NetworkError as e:
                print(f"  {e.message}", file=sys.stderr)
                if e.hint:
                    print(f"  → {e.hint}", file=sys.stderr)
            except Exception as e:
                print(f"  (не удалось загрузить список: {e})", file=sys.stderr)
            recent = get_recent_versions(root)
            if recent:
                print(f"  Недавно: {', '.join(recent)}")
            ver = input("Введите версию (например 3.12.0): ").strip()
            if not ver:
                continue
            with_pip = input("Установить pip в эту версию? (y/n) [n]: ").strip().lower() in ("y", "yes", "д", "да")
            try:
                install_embeddable(ver, root, with_pip=with_pip, progress=True)
                add_recent_version(root, ver)
                print("Готово.")
                print(f"Что нового: {_whatsnew_url(ver)}")
            except FileNotFoundError as e:
                _print_error(e, "Проверьте доступные версии: pyembed list -a")
                suggestions = _suggest_versions(ver)
                if suggestions:
                    print(f"  Возможно, вы имели в виду: {', '.join(suggestions[:5])}", file=sys.stderr)
            except NetworkError as e:
                _print_error(e, e.hint)
            except OSError as e:
                _print_error(e, "Проверьте права на запись в папку с версиями.")
            except Exception as e:
                _print_error(e)
            print()
            continue
        if choice == "2":
            ver = _choose_version_by_number(root, "Какую версию удалить? ")
            if ver:
                size_mb = get_version_dir_size(root, ver) // (1024 * 1024)
                print(f"  Освободится ~{size_mb} МБ.")
                confirm = input(f"Удалить {ver}? (y/n): ").strip().lower()
                if confirm in ("y", "yes", "д", "да"):
                    try:
                        uninstall_version(root, ver)
                        print("Удалено.")
                    except OSError as e:
                        _print_error(e, "Проверьте права на папку версии.")
                    except Exception as e:
                        _print_error(e)
            print()
            continue
        if choice == "3":
            ver = _choose_version_by_number(root, "Для какой версии запустить pip? ")
            if not ver:
                print()
                continue
            if not has_pip(root, ver):
                print(f"В {ver} нет pip. Установите pip через п. 4 или заново п. 1 с опцией pip.")
                print()
                continue
            exe = get_python_exe(root, ver)
            if not exe:
                print()
                continue
            print("Примеры: install requests, list, uninstall requests")
            pip_cmd = input("pip ").strip()
            if not pip_cmd:
                print()
                continue
            args = pip_cmd.split()
            subprocess.call([exe, "-m", "pip"] + args)
            add_recent_version(root, ver)
            print()
            continue
        if choice == "4":
            ver = _choose_version_by_number(root, "В какую версию установить pip? ")
            if ver:
                if has_pip(root, ver):
                    print(f"В {ver} уже установлен pip.")
                else:
                    try:
                        add_pip(root, ver, progress=True)
                        add_recent_version(root, ver)
                        print("Готово.")
                    except NetworkError as e:
                        _print_error(e, e.hint)
                    except OSError as e:
                        _print_error(e, "Проверьте права на запись в папку версии.")
                    except Exception as e:
                        _print_error(e)
            print()
            continue
        if choice == "5":
            ver = _choose_version_by_number(root, "Пакеты для какой версии? ")
            if not ver:
                print()
                continue
            if not has_pip(root, ver):
                print(f"В {ver} нет pip. Установите pip через п. 4 или п. 1 с опцией pip.")
                print()
                continue
            exe = get_python_exe(root, ver)
            if not exe:
                print()
                continue
            print("  list — список пакетов | add <pkg> — установить | remove <pkg> — удалить")
            line = input("packages ").strip()
            if not line:
                print()
                continue
            parts = line.split()
            if parts[0] == "list":
                subprocess.call([exe, "-m", "pip", "list"])
            elif parts[0] == "add" and len(parts) > 1:
                subprocess.call([exe, "-m", "pip", "install"] + parts[1:])
            elif parts[0] == "remove" and len(parts) > 1:
                subprocess.call([exe, "-m", "pip", "uninstall", "-y"] + parts[1:])
            else:
                print("Введите: list | add <pkg> ... | remove <pkg> ...")
            add_recent_version(root, ver)
            print()
            continue
        if choice == "6":
            ver = _choose_version_by_number(root, "На базе какой версии создать venv? ")
            if ver:
                exe = get_python_exe(root, ver)
                if exe:
                    name = input("Имя каталога окружения [.venv]: ").strip() or ".venv"
                    path = os.path.abspath(name)
                    if os.path.exists(path):
                        print(f"Каталог уже существует: {path}", file=sys.stderr)
                    else:
                        rc, used_virtualenv = _run_venv(exe, path, ver, root)
                        if rc == 0:
                            add_recent_version(root, ver)
                            suffix = " (через virtualenv)" if used_virtualenv else ""
                            print(f"Окружение создано{suffix}: {path}")
                            print(f"Активация (Windows): {name}\\Scripts\\activate")
            print()
            continue
        if choice == "7":
            if sys.platform != "win32":
                print("Управление PATH поддерживается только на Windows.")
                print()
                continue
            from .path_env import path_add, path_contains, path_remove, path_remove_duplicates

            sub_path = input("  1 — Добавить/убрать версию  2 — Убрать дубликаты в PATH  [1]: ").strip() or "1"
            if sub_path == "2":
                try:
                    n = path_remove_duplicates()
                    if n > 0:
                        print(f"Удалено дубликатов в PATH: {n}. Изменения в новых окнах консоли.")
                    else:
                        print("Дубликатов в PATH нет.")
                except Exception as e:
                    _print_error(e)
                print()
                continue

            ver = _choose_version_by_number(root, "Какую версию добавить в PATH или убрать? ")
            if not ver:
                print()
                continue
            exe = get_python_exe(root, ver)
            if not exe:
                print()
                continue
            dir_path: str = os.path.dirname(exe)
            if path_contains(dir_path):
                confirm = input(f"Убрать {ver} из PATH? (y/n): ").strip().lower()
                if confirm in ("y", "yes", "д", "да"):
                    try:
                        path_remove(dir_path)
                        add_recent_version(root, ver)
                        print("Удалено из PATH. Изменения в новых окнах консоли.")
                    except Exception as e:
                        _print_error(e)
            else:
                confirm = input(f"Добавить {ver} в PATH? (y/n): ").strip().lower()
                if confirm in ("y", "yes", "д", "да"):
                    try:
                        path_add(dir_path)
                        add_recent_version(root, ver)
                        print("Добавлено в PATH. Изменения в новых окнах консоли.")
                    except Exception as e:
                        _print_error(e)
            print()
            continue
        if choice == "8":
            ver = _choose_version_by_number(root, "Инфо о какой версии? ")
            if ver:
                exe = get_python_exe(root, ver)
                if exe:
                    dir_path = os.path.dirname(exe)
                    size_mb = get_version_dir_size(root, ver) / (1024 * 1024)
                    in_path = ""
                    if sys.platform == "win32":
                        try:
                            from .path_env import path_contains
                            in_path = " да" if path_contains(dir_path) else " нет"
                        except Exception:
                            in_path = " ?"
                    print(f"  Версия: {ver}")
                    print(f"  Путь:   {dir_path}")
                    print(f"  pip:    {'да' if has_pip(root, ver) else 'нет'}")
                    print(f"  Размер: {size_mb:.1f} МБ" + (f"  В PATH:{in_path}" if in_path else ""))
                else:
                    print(f"  Версия {ver} не установлена.", file=sys.stderr)
            print()
            continue
        if choice == "9":
            from .download import clear_cache, list_cache
            items = list_cache(root)
            if not items:
                print("  Кэш пуст.")
            else:
                print(f"  Кэш ({root}/.cache):")
                for name, size in items:
                    print(f"    {name}  {size / (1024 * 1024):.1f} МБ")
            action = input("  Очистить кэш? Версия (3.12.0), all — всё, Enter — не очищать: ").strip()
            if action:
                version_filter = None if action.lower() == "all" else action
                n = clear_cache(root, version_filter)
                if n > 0:
                    print(f"  Удалено файлов: {n}")
                else:
                    print("  В кэше нет файлов для этой версии (или кэш уже пуст).")
            print()
            continue
        if choice == "10":
            ver = _choose_version_by_number(root, "Обновить pip в какой версии? ")
            if ver:
                exe = get_python_exe(root, ver)
                if not exe:
                    print(f"  Версия {ver} не установлена.", file=sys.stderr)
                elif not has_pip(root, ver):
                    print(f"  В {ver} нет pip. Установите через п. 4.", file=sys.stderr)
                else:
                    subprocess.call([exe, "-m", "pip", "install", "--upgrade", "pip"])
                    add_recent_version(root, ver)
            print()
            continue
        print("Введите 1–11.")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pyembed",
        description="Менеджер портативных embeddable Python (скачивание в папку, без установки в систему).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Корневая папка для версий (по умолчанию: PYEMBED_ROOT или ./pythons).",
    )
    sub = parser.add_subparsers(dest="command", required=False)

    # list
    p_list = sub.add_parser("list", help="Показать установленные версии")
    p_list.add_argument("-a", "--available", action="store_true", help="Показать доступные на python.org")
    p_list.set_defaults(func=cmd_list)

    # which
    p_which = sub.add_parser("which", help="Путь к python.exe для версии (по умолчанию — из default)")
    p_which.add_argument("version", nargs="?", default=None, help="Версия (например 3.12.0)")
    p_which.add_argument("-c", "--copy", action="store_true", help="Скопировать путь в буфер обмена")
    p_which.set_defaults(func=cmd_which)

    # install
    p_install = sub.add_parser("install", help="Скачать и распаковать версию")
    p_install.add_argument("version", help="Версия, например 3.12.0")
    p_install.add_argument("--pip", action="store_true", help="Установить pip в эту версию")
    p_install.add_argument("-y", "--yes", action="store_true", help="Не выводить подсказку после установки (для скриптов/CI)")
    p_install.add_argument("--arch", choices=("amd64", "win32", "arm64"), default=None, help="Архитектура (по умолчанию: авто)")
    p_install.add_argument("--dry-run", action="store_true", help="Показать, что будет сделано, без загрузки и распаковки")
    p_install.set_defaults(func=cmd_install)

    # path (show / add / remove / list)
    p_path = sub.add_parser("path", help="Путь к версии и управление PATH")
    p_path_sub = p_path.add_subparsers(dest="path_action", required=True)
    p_path_show = p_path_sub.add_parser("show", help="Вывести путь к python.exe")
    p_path_show.add_argument("version", nargs="?", default=None, help="Версия (если не указана — по умолчанию)")
    p_path_show.add_argument("-c", "--copy", action="store_true", help="Скопировать путь в буфер обмена")
    p_path_show.set_defaults(func=cmd_path_show)
    p_path_add = p_path_sub.add_parser("add", help="Добавить версию в PATH пользователя (Windows)")
    p_path_add.add_argument("version", help="Версия, например 3.12.0")
    p_path_add.set_defaults(func=cmd_path_add)
    p_path_remove = p_path_sub.add_parser("remove", help="Убрать версию из PATH пользователя (Windows)")
    p_path_remove.add_argument("version", help="Версия, например 3.12.0")
    p_path_remove.set_defaults(func=cmd_path_remove)
    p_path_list = p_path_sub.add_parser("list", help="Показать версии из этого корня, которые в PATH")
    p_path_list.set_defaults(func=cmd_path_list)
    p_path_fix_duplicates = p_path_sub.add_parser(
        "fix-duplicates",
        help="Удалить дубликаты записей в PATH пользователя (Windows)",
    )
    p_path_fix_duplicates.set_defaults(func=cmd_path_fix_duplicates)

    # copy — скопировать версию в папку (например C:/Python/3.15) и в PATH
    p_copy = sub.add_parser(
        "copy",
        help="Скопировать версию в папку (например C:/Python/3.15) и добавить в PATH (Windows)",
    )
    p_copy.add_argument("version", help="Версия, например 3.15.0")
    p_copy.add_argument(
        "dest",
        nargs="?",
        default=None,
        help="Папка назначения (по умолчанию: C:/Python/<версия>)",
    )
    p_copy.add_argument("--force", action="store_true", help="Перезаписать папку, если существует")
    p_copy.add_argument("--no-path", action="store_true", help="Не добавлять папку в PATH")
    p_copy.add_argument("--dry-run", action="store_true", help="Показать, что будет сделано, без выполнения")
    p_copy.set_defaults(func=cmd_copy)

    # packages (list / add / remove)
    p_packages = sub.add_parser("packages", help="Управление пакетами (pip) для версии")
    p_packages.add_argument("version", help="Версия Python, например 3.12.0")
    p_packages_sub = p_packages.add_subparsers(dest="packages_action", required=True)
    p_pkg_list = p_packages_sub.add_parser("list", help="Список установленных пакетов")
    p_pkg_list.set_defaults(func=cmd_packages_list)
    p_pkg_add = p_packages_sub.add_parser("add", help="Установить пакет(ы)")
    p_pkg_add.add_argument("packages", nargs="*", help="Имена пакетов (pip install)")
    p_pkg_add.set_defaults(func=cmd_packages_add)
    p_pkg_remove = p_packages_sub.add_parser("remove", help="Удалить пакет(ы)")
    p_pkg_remove.add_argument("packages", nargs="*", help="Имена пакетов (pip uninstall)")
    p_pkg_remove.set_defaults(func=cmd_packages_remove)

    # run
    p_run = sub.add_parser("run", help="Запустить python указанной версии с аргументами")
    p_run.add_argument("version", nargs="?", default=None, help="Версия (если не указана — версия по умолчанию)")
    p_run.add_argument("rest", nargs=argparse.REMAINDER, help="Аргументы для python")
    p_run.set_defaults(func=cmd_run)

    # use
    p_use = sub.add_parser("use", help="Подсказка: как добавить версию в PATH")
    p_use.add_argument("version", help="Версия, например 3.12.0")
    p_use.add_argument("-c", "--copy", action="store_true", help="Скопировать путь каталога в буфер обмена")
    p_use.set_defaults(func=cmd_use)

    # uninstall
    p_uninstall = sub.add_parser("uninstall", help="Удалить установленную версию")
    p_uninstall.add_argument("version", help="Версия для удаления")
    p_uninstall.add_argument("-y", "--yes", dest="force", action="store_true", help="Без подтверждения")
    p_uninstall.set_defaults(func=cmd_uninstall)

    # verify
    p_verify = sub.add_parser("verify", help="Проверить целостность установленной версии")
    p_verify.add_argument("version", nargs="?", default=None, help="Версия (если не указана — по умолчанию)")
    p_verify.set_defaults(func=cmd_verify)

    # pip
    p_pip = sub.add_parser("pip", help="Запустить pip для указанной версии")
    p_pip.add_argument("version", help="Версия Python, например 3.12.0")
    p_pip.add_argument("pip_args", nargs=argparse.REMAINDER, help="Аргументы для pip (install, list, uninstall ...)")
    p_pip.set_defaults(func=cmd_pip)

    # add-pip
    p_add_pip = sub.add_parser("add-pip", help="Установить pip в уже установленную версию")
    p_add_pip.add_argument("version", help="Версия Python, например 3.12.0")
    p_add_pip.set_defaults(func=cmd_add_pip)

    # upgrade-pip
    p_upgrade_pip = sub.add_parser("upgrade-pip", help="Обновить pip в установленной версии")
    p_upgrade_pip.add_argument("version", nargs="?", default=None, help="Версия (по умолчанию — из default)")
    p_upgrade_pip.set_defaults(func=cmd_upgrade_pip)

    # cache
    p_cache = sub.add_parser("cache", help="Кэш скачанных архивов")
    p_cache_sub = p_cache.add_subparsers(dest="cache_action", required=True)
    p_cache_list = p_cache_sub.add_parser("list", help="Показать файлы в кэше")
    p_cache_list.set_defaults(func=cmd_cache_list)
    p_cache_clear = p_cache_sub.add_parser("clear", help="Очистить кэш")
    p_cache_clear.add_argument("version", nargs="?", default=None, help="Очистить только для версии (например 3.12.0)")
    p_cache_clear.set_defaults(func=cmd_cache_clear)

    # info
    p_info = sub.add_parser("info", help="Информация о версии (путь, pip, размер, PATH)")
    p_info.add_argument("version", nargs="?", default=None, help="Версия (по умолчанию — из default)")
    p_info.set_defaults(func=cmd_info)

    # doctor
    p_doctor = sub.add_parser("doctor", help="Проверка: сеть, диск, целостность версий, PATH")
    p_doctor.add_argument("--fix", action="store_true", help="Исправить дубликаты в PATH (Windows)")
    p_doctor.set_defaults(func=cmd_doctor)

    # ide — путь для Cursor / VS Code
    p_ide = sub.add_parser("ide", help="Путь к интерпретатору для Cursor/VS Code (python.defaultInterpreterPath)")
    p_ide.add_argument("version", nargs="?", default=None, help="Версия (по умолчанию — из default)")
    p_ide.add_argument("--json", action="store_true", help="Вывести только JSON для settings.json")
    p_ide.set_defaults(func=cmd_ide)

    # default
    p_default = sub.add_parser("default", help="Показать или задать версию по умолчанию (для run без версии)")
    p_default.add_argument("version", nargs="?", default=None, help="Версия для сохранения (если не указана — показать текущую)")
    p_default.set_defaults(func=cmd_default)

    # venv
    p_venv = sub.add_parser("venv", help="Создать виртуальное окружение (venv) от выбранной версии")
    p_venv.add_argument("version", help="Версия Python, например 3.12.0")
    p_venv.add_argument(
        "name",
        nargs="?",
        default=".venv",
        help="Имя каталога окружения (по умолчанию: .venv)",
    )
    p_venv.set_defaults(func=cmd_venv)

    args = parser.parse_args()
    if args.root is not None:
        os.environ["PYEMBED_ROOT"] = args.root

    if args.command is None:
        # Windowed/GUI exe has no console — показываем окно вместо интерактивного меню
        if sys.stdin is None or getattr(sys.stdin, "closed", True):
            try:
                from .gui import run_gui
                return run_gui()
            except Exception as e:
                _show_no_console_message()
                if sys.stderr and not getattr(sys.stderr, "closed", True):
                    print(f"GUI failed: {e}", file=sys.stderr)
                return 1
        return run_interactive()

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
