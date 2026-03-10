"""Управление переменной PATH пользователя (Windows)."""
import os
import sys

if sys.platform == "win32":
    import winreg
else:
    winreg = None  # type: ignore


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Управление PATH (add/remove) поддерживается только на Windows.")


def _get_user_path_value() -> str:
    """Читает значение Path из реестра пользователя (HKCU)."""
    _require_windows()
    assert winreg is not None
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ,
        )
        try:
            value, _ = winreg.QueryValueEx(key, "Path")
            return value or ""
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return ""


def _set_user_path_value(value: str) -> None:
    """Записывает значение Path в реестр пользователя (HKCU)."""
    _require_windows()
    assert winreg is not None
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Environment",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, value)
    finally:
        winreg.CloseKey(key)


def _normalize_path(p: str) -> str:
    return os.path.normpath(os.path.abspath(p))


def get_user_path_entries() -> list[str]:
    """Возвращает список каталогов в PATH пользователя (нормализованные)."""
    raw = _get_user_path_value()
    return [_normalize_path(part) for part in raw.split(os.pathsep) if part.strip()]


def set_user_path_entries(entries: list[str]) -> None:
    """Записывает список каталогов в PATH пользователя."""
    value = os.pathsep.join(entries)
    _set_user_path_value(value)


def path_add(dir_path: str) -> bool:
    """
    Добавляет каталог в PATH пользователя (в начало).
    Возвращает True, если PATH изменился.
    """
    norm = _normalize_path(dir_path)
    entries = get_user_path_entries()
    if norm in entries:
        return False
    entries.insert(0, norm)
    set_user_path_entries(entries)
    return True


def path_remove(dir_path: str) -> bool:
    """
    Удаляет каталог из PATH пользователя.
    Возвращает True, если PATH изменился.
    """
    norm = _normalize_path(dir_path)
    entries = get_user_path_entries()
    new_entries = [e for e in entries if e != norm]
    if len(new_entries) == len(entries):
        return False
    set_user_path_entries(new_entries)
    return True


def path_contains(dir_path: str) -> bool:
    """Проверяет, есть ли каталог в PATH пользователя."""
    norm = _normalize_path(dir_path)
    return norm in get_user_path_entries()


def path_remove_duplicates() -> int:
    """
    Удаляет дубликаты записей из PATH пользователя (сохраняя порядок, первое вхождение остаётся).
    Возвращает число удалённых дубликатов.
    """
    _require_windows()
    entries = get_user_path_entries()
    seen: set[str] = set()
    new_entries: list[str] = []
    removed = 0
    for e in entries:
        if e in seen:
            removed += 1
            continue
        seen.add(e)
        new_entries.append(e)
    if removed > 0:
        set_user_path_entries(new_entries)
    return removed


def path_list_missing() -> list[str]:
    """Возвращает записи PATH, указывающие на несуществующие каталоги."""
    _require_windows()
    entries = get_user_path_entries()
    missing: list[str] = []
    for e in entries:
        check = os.path.expandvars(e) if "%" in e else e
        if not os.path.isdir(check):
            missing.append(e)
    return missing


def path_remove_missing() -> list[str]:
    """
    Удаляет из PATH пользователя записи, указывающие на несуществующие каталоги.
    Возвращает список удалённых путей.
    """
    _require_windows()
    entries = get_user_path_entries()
    existing: list[str] = []
    missing: list[str] = []
    for e in entries:
        check = os.path.expandvars(e) if "%" in e else e
        if os.path.isdir(check):
            existing.append(e)
        else:
            missing.append(e)
    if missing:
        set_user_path_entries(existing)
    return missing
