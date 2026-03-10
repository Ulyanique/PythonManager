"""Работа с уже установленными версиями в папке менеджера."""
import os
import shutil

from .version_util import version_sort_key


def list_installed(root_dir: str) -> list[str]:
    """Возвращает список установленных версий (по каталогам с python.exe)."""
    if not os.path.isdir(root_dir):
        return []
    versions: list[str] = []
    for name in os.listdir(root_dir):
        path = os.path.join(root_dir, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "python.exe")):
            versions.append(name)
    return sorted(versions, key=version_sort_key, reverse=True)

def get_python_exe(root_dir: str, version: str) -> str | None:
    exe = os.path.join(root_dir, version, "python.exe")
    return exe if os.path.isfile(exe) else None

def get_version_dir(root_dir: str, version: str) -> str:
    return os.path.join(root_dir, version)

def has_pip(root_dir: str, version: str) -> bool:
    """Проверяет, установлен ли pip в этой версии (есть Lib/site-packages с pip)."""
    base = os.path.join(root_dir, version)
    site = os.path.join(base, "Lib", "site-packages")
    if not os.path.isdir(site):
        return False
    return any(
        name.startswith("pip") and not name.startswith("pip-")
        for name in os.listdir(site)
    ) or os.path.isfile(os.path.join(site, "pip", "__init__.py"))

def uninstall_version(root_dir: str, version: str) -> bool:
    """Удаляет каталог версии. Возвращает True при успехе."""
    path = get_version_dir(root_dir, version)
    if not os.path.isdir(path):
        return False
    shutil.rmtree(path)
    return True


def verify_version(root_dir: str, version: str) -> tuple[bool, list[str]]:
    """
    Проверяет целостность установленной версии (наличие python.exe и ключевых файлов).
    Возвращает (ok, список недостающих или повреждённых пунктов).
    """
    missing: list[str] = []
    version_dir = get_version_dir(root_dir, version)
    if not os.path.isdir(version_dir):
        return False, [f"Каталог {version_dir} не найден"]
    exe = os.path.join(version_dir, "python.exe")
    if not os.path.isfile(exe):
        missing.append("python.exe")
    # Ключевая DLL: python3XX.dll (major.minor из версии)
    parts = version.split(".")
    if len(parts) >= 2:
        major_minor = parts[0] + parts[1]
        dll_name = f"python{major_minor}.dll"
        dll_path = os.path.join(version_dir, dll_name)
        if not os.path.isfile(dll_path):
            missing.append(dll_name)
    return len(missing) == 0, missing


def get_version_dir_size(root_dir: str, version: str) -> int:
    """Размер каталога версии в байтах (сумма файлов)."""
    version_dir = get_version_dir(root_dir, version)
    if not os.path.isdir(version_dir):
        return 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(version_dir):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def copy_version_to(root_dir: str, version: str, dest: str, force: bool = False) -> str:
    """
    Копирует установленную версию в папку dest (например C:/Python/3.15).
    Возвращает нормализованный путь к dest.
    При существующем dest и force=False выбрасывает FileExistsError.
    """
    src = get_version_dir(root_dir, version)
    if not os.path.isdir(src):
        raise FileNotFoundError(f"Версия {version} не установлена: {src}")
    dest_abs = os.path.normpath(os.path.abspath(dest))
    if os.path.exists(dest_abs):
        if not force:
            raise FileExistsError(f"Папка уже существует: {dest_abs}. Используйте --force для перезаписи.")
        if os.path.isdir(dest_abs):
            shutil.rmtree(dest_abs)
        else:
            os.remove(dest_abs)
    shutil.copytree(src, dest_abs)
    return dest_abs
