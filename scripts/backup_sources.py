#!/usr/bin/env python3
"""
Бэкап исходников проекта без загруженного материала (pythons, кэш, venv и т.д.).
Сохраняет zip в папку backups/ с именем pyembed-vYY.MM.DD.HHMM.zip (год.месяц.день.часминута).

Запуск из корня проекта: python scripts/backup_sources.py
"""
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUPS_DIR = ROOT / "backups"

# Исключаем: загруженное, кэш, окружения, артефакты сборки, сами бэкапы
EXCLUDE_DIRS = {
    "pythons",       # загруженные embed-версии
    ".cache",        # кэш архивов (внутри pythons или корня)
    "backups",       # папка бэкапов
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".git",
}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".egg-info")
EXCLUDE_FILES = {".pyembed-recent"}  # в корне или в pythons


def should_skip(path: Path, base: Path) -> bool:
    """Пропускать ли путь (каталог или файл)."""
    rel = path.relative_to(base)
    parts = rel.parts
    if parts and parts[0] in EXCLUDE_DIRS:
        return True
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    if path.is_file():
        if path.suffix in (".pyc", ".pyo"):
            return True
        if path.name.endswith(".egg-info") or path.name == ".pyembed-recent":
            return True
    return False


def run_backup() -> tuple[Path, int, float]:
    """
    Создать бэкап. Возвращает (путь к архиву, число файлов, размер в МБ).
    """
    BACKUPS_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    version = f"v{now:%y.%m.%d.%H%M}"  # v26.03.11.1002
    archive_name = f"pyembed-{version}.zip"
    archive_path = BACKUPS_DIR / archive_name

    count = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in ROOT.rglob("*"):
            if f == archive_path or f == ROOT:
                continue
            if should_skip(f, ROOT):
                continue
            if not f.is_file():
                continue
            try:
                arcname = f.relative_to(ROOT)
                zf.write(f, arcname)
                count += 1
            except OSError:
                pass

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    return (archive_path, count, size_mb)


def main() -> int:
    path, count, size_mb = run_backup()
    print(f"Создан бэкап: {path}")
    print(f"  Файлов: {count}, размер: {size_mb:.2f} МБ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
