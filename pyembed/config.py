"""Paths and defaults for the embeddable Python manager."""
import os

# Каталог, куда складываются все версии (портативная папка)
DEFAULT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pythons")

DEFAULT_VERSION_FILE = ".pyembed-default"
RECENT_VERSIONS_FILE = ".pyembed-recent"
RECENT_MAX = 5


def get_root() -> str:
    env_root = os.environ.get("PYEMBED_ROOT", "")
    if env_root and os.path.isabs(env_root):
        return os.path.normpath(env_root)
    if env_root:
        return os.path.normpath(os.path.join(os.getcwd(), env_root))
    return os.path.normpath(os.path.abspath(DEFAULT_ROOT))


def get_default_version(root: str) -> str | None:
    """Читает сохранённую версию по умолчанию из root/.pyembed-default."""
    path = os.path.join(root, DEFAULT_VERSION_FILE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            version = f.read().strip()
        return version if version else None
    except OSError:
        return None


def set_default_version(root: str, version: str) -> None:
    """Сохраняет версию по умолчанию в root/.pyembed-default."""
    path = os.path.join(root, DEFAULT_VERSION_FILE)
    os.makedirs(root, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(version.strip() + "\n")


def get_recent_versions(root: str) -> list[str]:
    """Читает список недавно использованных версий (новые первые)."""
    path = os.path.join(root, RECENT_VERSIONS_FILE)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()][:RECENT_MAX]
    except OSError:
        return []


def add_recent_version(root: str, version: str) -> None:
    """Добавляет версию в начало списка недавних (без дубликатов, макс. RECENT_MAX)."""
    recent = [version.strip()] + [v for v in get_recent_versions(root) if v != version.strip()][: RECENT_MAX - 1]
    path = os.path.join(root, RECENT_VERSIONS_FILE)
    os.makedirs(root, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(recent) + "\n")
