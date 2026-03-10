"""Download and extract Python embeddable packages from python.org."""
import os
import re
import shutil
import socket
import zipfile
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

from .version_util import version_sort_key

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    requests = None  # type: ignore[assignment]
    _HAS_REQUESTS = False


class NetworkError(Exception):
    """Ошибка загрузки с подсказкой для пользователя."""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.hint = hint

BASE_FTP = "https://www.python.org/ftp/python"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
# Для Python < 3.9 нужен versioned get-pip (текущий использует синтаксис 3.9+)
GET_PIP_VERSIONED = "https://bootstrap.pypa.io/pip/{major}.{minor}/get-pip.py"


def _get_pip_url(version: str) -> str:
    """URL get-pip.py: для 3.5–3.8 — versioned, для 3.9+ — общий."""
    parts = version.split(".")
    if len(parts) < 2:
        return GET_PIP_URL
    try:
        major, minor = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return GET_PIP_URL
    if major == 3 and minor < 9:
        return GET_PIP_VERSIONED.format(major=major, minor=minor)
    return GET_PIP_URL
CACHE_DIR_NAME = ".cache"
MIN_FREE_BYTES = 100 * 1024 * 1024  # 100 МБ перед загрузкой
MAX_HTML_BYTES = 2 * 1024 * 1024  # макс. размер страницы списка версий (2 МБ)
DOWNLOAD_RETRIES = 2  # повторов при сбое (всего 3 попытки)


def get_cache_dir(root_dir: str) -> str:
    return os.path.join(root_dir, CACHE_DIR_NAME)


def list_cache(root_dir: str) -> list[tuple[str, int]]:
    """Список файлов в кэше: (имя, размер в байтах)."""
    cache_dir = get_cache_dir(root_dir)
    if not os.path.isdir(cache_dir):
        return []
    result: list[tuple[str, int]] = []
    for name in os.listdir(cache_dir):
        path = os.path.join(cache_dir, name)
        if os.path.isfile(path):
            try:
                result.append((name, os.path.getsize(path)))
            except OSError:
                pass
    return sorted(result, key=lambda x: x[0])


def clear_cache(root_dir: str, version: str | None = None) -> int:
    """Удаляет файлы из кэша. Если version задана — только этот архив. Возвращает число удалённых файлов."""
    cache_dir = get_cache_dir(root_dir)
    if not os.path.isdir(cache_dir):
        return 0
    removed = 0
    for name in os.listdir(cache_dir):
        if version and version not in name:
            continue
        path = os.path.join(cache_dir, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed += 1
            except OSError:
                pass
    return removed

def _detect_arch() -> str:
    import platform
    m = platform.machine().lower()
    if m in ("amd64", "x86_64"):
        return "amd64"
    if m == "arm64" or m == "aarch64":
        return "arm64"
    return "win32"

def _version_base_path(version: str) -> str:
    """Для pre-release (3.15.0a4) возвращает базовый путь каталога (3.15.0)."""
    m = re.match(r"^(\d+\.\d+\.\d+)", version.strip())
    return m.group(1) if m else version


def embed_url(version: str, arch: str | None = None) -> str:
    """URL архива на python.org. Для 3.15.0a4 каталог — 3.15.0, файл — с суффиксом a4."""
    if arch is None:
        arch = _detect_arch()
    base = _version_base_path(version)
    return f"{BASE_FTP}/{base}/python-{version}-embed-{arch}.zip"

def _parse_ftp_listing(html: str) -> list[str]:
    """Из HTML-листинга FTP извлекаем номера версий (3.12.0/, 3.15.0a4/ и т.д.)."""
    # Ссылки вида href="3.12.0/" или href="3.15.0a4/"
    pattern = re.compile(r'href="(\d+\.\d+\.\d+(?:a\d*|b\d*|rc\d*)?)/"')
    versions: list[str] = []
    for m in pattern.finditer(html):
        v = m.group(1)
        if v not in versions:
            versions.append(v)
    return sorted(versions, key=version_sort_key, reverse=True)

def _network_error_message(exc: Exception, context: str = "загрузка") -> tuple[str, str]:
    """Возвращает (сообщение, подсказка) для типичных сетевых ошибок."""
    if isinstance(exc, HTTPError):
        if exc.code == 404:
            return (
                f"Версия не найдена по указанному URL (404).",
                "Проверьте доступные версии: pyembed list -a",
            )
        if exc.code == 403:
            return (
                "Доступ запрещён (403).",
                "Возможно, для этой версии нет embeddable-пакета под вашу ОС.",
            )
        if 500 <= exc.code < 600:
            return (
                "Сервер python.org временно недоступен.",
                "Повторите попытку через несколько минут.",
            )
        return (f"Ошибка HTTP {exc.code}.", "Повторите позже.")
    if isinstance(exc, URLError):
        reason_str = str(exc.reason) if exc.reason else ""
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            return (
                "Истекло время ожидания при загрузке.",
                "Проверьте интернет-соединение и повторите.",
            )
        if "getaddrinfo" in reason_str or "Name or service not known" in reason_str:
            return (
                "Не удаётся связаться с python.org.",
                "Проверьте интернет и DNS (доступность www.python.org).",
            )
        if "Connection refused" in reason_str or "Connection reset" in reason_str:
            return (
                "Соединение с сервером не установлено.",
                "Проверьте интернет, файрвол и повторите.",
            )
        return (
            f"Ошибка при {context}: {exc.reason}",
            "Проверьте интернет и повторите.",
        )
    return (str(exc), "Повторите позже.")


def fetch_versions() -> list[str]:
    """Список доступных версий с FTP (стабильные 3.x). Чтение ограничено MAX_HTML_BYTES."""
    headers = {"User-Agent": "Python-Embeddable-Manager/1.0"}
    url = f"{BASE_FTP}/"
    try:
        if _HAS_REQUESTS and requests is not None:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            html = r.content[:MAX_HTML_BYTES].decode("utf-8", errors="replace")
        else:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                chunks: list[bytes] = []
                total = 0
                while total < MAX_HTML_BYTES:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                html = b"".join(chunks).decode("utf-8", errors="replace")
    except HTTPError as e:
        msg, hint = _network_error_message(e, "получении списка версий")
        raise NetworkError(msg, hint) from e
    except URLError as e:
        msg, hint = _network_error_message(e, "получении списка версий")
        raise NetworkError(msg, hint) from e
    except Exception as e:
        if _HAS_REQUESTS and isinstance(e, requests.RequestException):  # type: ignore[union-attr]
            msg, hint = _network_error_message(e, "получении списка версий")
            raise NetworkError(msg, hint) from e
        raise
    raw = _parse_ftp_listing(html)
    # Показываем только версии, для которых на python.org есть Windows embed (3.5+)
    return [v for v in raw if v.startswith("3.") and _version_has_embed(v)]


def _version_has_embed(version: str) -> bool:
    """True, если для этой версии на python.org выкладывают Windows embed-пакет (начиная с 3.5)."""
    parts = version.split(".")
    if len(parts) < 2:
        return True
    try:
        major, minor = int(parts[0]), int(parts[1])
        return major > 3 or (major == 3 and minor >= 5)
    except (ValueError, IndexError):
        return True

def resolve_version_for_install(version: str) -> str:
    """
    Преобразует короткую версию в полную: «3.9» → последняя 3.9.x, «3» → последняя 3.x.
    Полная версия (3.12.0) возвращается без изменений, если есть в списке.
    """
    version = version.strip()
    parts = version.split(".")
    available = fetch_versions()
    # Полная версия (3.12.0 или 3.15.0a4) — как есть, если есть в списке
    if len(parts) >= 3 and version in available:
        return version
    # Префикс для поиска: «3» → "3.", «3.9» → "3.9.", «3.12.0» (нет в списке) → "3.12."
    if len(parts) >= 2:
        prefix = parts[0] + "." + parts[1] + "."
    elif parts and parts[0]:
        prefix = parts[0] + "."
    else:
        raise FileNotFoundError("Укажите версию (например 3.12 или 3.12.0).")
    # Windows embed-пакеты на python.org есть только начиная с Python 3.5.
    if prefix in ("3.4.", "3.3.", "3.2.", "3.1.", "3.0."):
        raise FileNotFoundError(
            f"Для Python {prefix.rstrip('.')} нет Windows embed-пакета на python.org. "
            "Минимальная версия с embed: 3.5. Используйте: pyembed install 3.5"
        )
    matching = [v for v in available if v.startswith(prefix)]
    if not matching:
        raise FileNotFoundError(
            f"Нет доступных версий для «{version}». Проверьте: pyembed list -a"
        )
    chosen = matching[0]
    # У старых линеек (3.8, 3.7, …) не все patch-релизы имеют Windows embed на python.org.
    # Возвращаем последнюю версию, для которой embed точно есть.
    if prefix == "3.8.":
        chosen = "3.8.10"
    elif prefix == "3.7.":
        chosen = "3.7.9"
    elif prefix == "3.6.":
        chosen = "3.6.8"
    elif prefix == "3.5.":
        chosen = "3.5.4"
    return chosen


def _check_free_space(root_dir: str, need_bytes: int) -> None:
    """Проверяет свободное место. При нехватке выбрасывает RuntimeError."""
    try:
        usage = shutil.disk_usage(os.path.abspath(root_dir))
        if usage.free < need_bytes + MIN_FREE_BYTES:
            raise RuntimeError(
                f"Мало свободного места: {usage.free // (1024*1024)} МБ. "
                f"Нужно около {need_bytes // (1024*1024)} МБ + запас."
            )
    except OSError:
        pass


def _fetch_content_length(url: str) -> int | None:
    """Размер по Content-Length (HEAD), иначе None."""
    req = Request(url, method="HEAD", headers={"User-Agent": "Python-Embeddable-Manager/1.0"})
    try:
        with urlopen(req, timeout=10) as r:
            return int(r.headers.get("Content-Length", 0)) or None
    except Exception:
        return None


def _get_fallback_versions(version: str) -> list[str]:
    """
    Список patch-версий той же линейки (3.8.x), от новых к старым, без текущей.
    Генерируем по номерам patch, без зависимости от fetch_versions() (в листинге
    могут отсутствовать старые версии, у которых есть embed).
    """
    parts = version.split(".")
    if len(parts) < 3:
        return []
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        return []
    return [f"{major}.{minor}.{p}" for p in range(patch - 1, -1, -1)]


def _resolve_embed_version(version: str, arch: str | None) -> str:
    """
    Возвращает версию, для которой на python.org есть embed-архив.
    Если для version нет (404), перебирает patch-версии той же линейки, затем предыдущий minor.
    Например, для 3.15.0 без embed пробуем 3.14.x.
    """
    url = embed_url(version, arch)
    req = Request(url, method="HEAD", headers={"User-Agent": "Python-Embeddable-Manager/1.0"})
    try:
        with urlopen(req, timeout=15):
            return version
    except HTTPError:
        pass
    except (URLError, OSError):
        return version  # сеть/таймаут — пусть дальше попробует скачать
    for fb in _get_fallback_versions(version):
        url_fb = embed_url(fb, arch)
        req_fb = Request(url_fb, method="HEAD", headers={"User-Agent": "Python-Embeddable-Manager/1.0"})
        try:
            with urlopen(req_fb, timeout=15):
                return fb
        except (HTTPError, URLError, OSError):
            continue
    # В этой линейке embed нет (например 3.15.0 ещё не выложен) — пробуем предыдущий minor
    parts = version.split(".")
    if len(parts) >= 2:
        try:
            major, minor = int(parts[0]), int(parts[1])
            if minor > 0:
                prev_prefix = f"{major}.{minor - 1}."
                available = fetch_versions()
                for v in available:
                    if v.startswith(prev_prefix):
                        req_prev = Request(
                            embed_url(v, arch),
                            method="HEAD",
                            headers={"User-Agent": "Python-Embeddable-Manager/1.0"},
                        )
                        try:
                            with urlopen(req_prev, timeout=15):
                                return v
                        except (HTTPError, URLError, OSError):
                            continue
        except (ValueError, IndexError):
            pass
    return version  # не нашли — вернём исходную, дальше будет 404


def download_file(url: str, dest_path: str, progress: bool = True) -> None:
    req = Request(url, headers={"User-Agent": "Python-Embeddable-Manager/1.0"})
    last_err: BaseException | None = None
    for attempt in range(DOWNLOAD_RETRIES + 1):
        try:
            with urlopen(req, timeout=60) as r:
                total = int(r.headers.get("Content-Length", 0)) or None
                chunk_size = 1024 * 256
                read = 0
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = r.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        read += len(chunk)
                        if progress and total and total > 0:
                            pct = min(100, read * 100 // total)
                            print(f"\r  Загрузка: {pct}%", end="", flush=True)
            if progress:
                print()
            return
        except HTTPError as e:
            if e.code == 404:
                raise
            last_err = e
        except (URLError, OSError) as e:
            last_err = e
        if os.path.isfile(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        if attempt < DOWNLOAD_RETRIES and last_err is not None:
            if progress:
                print(f"\r  Повтор {attempt + 2}/{DOWNLOAD_RETRIES + 1}...", end="", flush=True)
    if last_err is not None:
        raise last_err

def check_zip_integrity(zip_path: str) -> None:
    """
    Проверяет, что файл — валидный zip и все записи читаются.
    При ошибке удаляет файл и поднимает OSError (чтобы не переиспользовать битый кэш).
    """
    if not zipfile.is_zipfile(zip_path):
        try:
            os.remove(zip_path)
        except OSError:
            pass
        raise OSError(f"Файл не является корректным zip-архивом или повреждён: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as z:
        bad = z.testzip()
        if bad is not None:
            try:
                os.remove(zip_path)
            except OSError:
                pass
            raise OSError(f"Повреждённый архив (битый файл внутри): {bad}")


def extract_zip(zip_path: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)

def install_embeddable(
    version: str,
    root_dir: str,
    arch: str | None = None,
    with_pip: bool = False,
    progress: bool = True,
    dry_run: bool = False,
) -> str:
    """
    Скачивает и распаковывает embeddable Python в root_dir/version.
    Короткая версия («3.9», «3») заменяется на новейшую доступную (3.9.x или 3.x).
    Опционально устанавливает pip. Возвращает путь к каталогу установки.
    При dry_run=True только выводит план и возвращает путь без загрузки.
    """
    version = resolve_version_for_install(version)
    arch_actual = arch if arch is not None else _detect_arch()
    requested = version
    version = _resolve_embed_version(version, arch_actual)
    if version != requested and progress:
        print(
            f"Версия {requested} без embed-пакета на python.org, используем {version}.",
            flush=True,
        )
    url = embed_url(version, arch_actual)
    version_dir = os.path.join(root_dir, version)
    if dry_run:
        print(f"[dry-run] Будет загружено: {url}")
        print(f"[dry-run] Будет распаковано в: {version_dir}")
        if with_pip:
            print("[dry-run] Будет установлен pip")
        return version_dir
    if os.path.isdir(version_dir) and os.path.isfile(
        os.path.join(version_dir, "python.exe")
    ):
        if progress:
            print(f"Версия {version} уже установлена: {version_dir}")
        if with_pip:
            _ensure_pip(version_dir, version, progress=progress)
        return version_dir

    os.makedirs(root_dir, exist_ok=True)
    cache_dir = get_cache_dir(root_dir)
    zip_path = os.path.join(cache_dir, f"python-{version}-embed-{arch_actual}.zip")

    zip_created_this_run = False
    try:
        if not os.path.isfile(zip_path):
            size = _fetch_content_length(url) or (80 * 1024 * 1024)
            _check_free_space(root_dir, size)
            os.makedirs(cache_dir, exist_ok=True)
            if progress:
                print(f"Загрузка {version} из {url}", flush=True)
            try:
                download_file(url, zip_path, progress=progress)
                zip_created_this_run = True
            except HTTPError as e:
                if e.code == 404:
                    fallbacks = _get_fallback_versions(version)
                    if progress and fallbacks:
                        print(
                            f"Версия {version} без embed-пакета на python.org, "
                            f"пробуем другую 3.{version.split('.')[1]}.x…"
                        )
                    for fallback in fallbacks:
                        url_fb = embed_url(fallback, arch_actual)
                        zip_path_fb = os.path.join(
                            cache_dir, f"python-{fallback}-embed-{arch_actual}.zip"
                        )
                        try:
                            download_file(url_fb, zip_path_fb, progress=progress)
                            if progress:
                                print(f"Установлена версия {fallback}.")
                            version = fallback
                            zip_path = zip_path_fb
                            version_dir = os.path.join(root_dir, version)
                            zip_created_this_run = True
                            break
                        except (HTTPError, URLError, OSError):
                            continue
                    else:
                        raise FileNotFoundError(
                            f"Версия {version} не найдена. Проверьте: pyembed list -a"
                        ) from e
                else:
                    msg, hint = _network_error_message(e)
                    raise NetworkError(msg, hint) from e
            except URLError as e:
                msg, hint = _network_error_message(e)
                raise NetworkError(msg, hint) from e
        elif progress:
            print(f"Используется кэш: {zip_path}")

        check_zip_integrity(zip_path)
        if progress:
            print(f"Распаковка в {version_dir}", flush=True)
        extract_zip(zip_path, version_dir)

        if with_pip:
            _ensure_pip(version_dir, version, progress=progress)

        return version_dir
    except KeyboardInterrupt:
        if progress:
            print("\nПрервано. Очистка...", file=__import__("sys").stderr)
        if os.path.isdir(version_dir):
            try:
                shutil.rmtree(version_dir)
            except OSError:
                pass
        if zip_created_this_run and os.path.isfile(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass
        raise


def add_pip(root_dir: str, version: str, progress: bool = True) -> None:
    """Устанавливает pip в уже установленную embeddable-версию."""
    version_dir = os.path.join(root_dir, version)
    if not os.path.isdir(version_dir) or not os.path.isfile(
        os.path.join(version_dir, "python.exe")
    ):
        raise FileNotFoundError(f"Версия {version} не установлена: {version_dir}")
    _ensure_pip(version_dir, version, progress=progress)


def _ensure_pip(version_dir: str, version: str, progress: bool = True) -> None:
    """Устанавливает pip в embeddable: get-pip.py и правка ._pth."""
    import subprocess
    python_exe = os.path.join(version_dir, "python.exe")
    get_pip = os.path.join(version_dir, "get-pip.py")
    if not os.path.isfile(python_exe):
        return
    # Скачать get-pip.py (для 3.5–3.8 — versioned URL)
    if not os.path.isfile(get_pip):
        if progress:
            print("  Загрузка get-pip.py")
        download_file(_get_pip_url(version), get_pip, progress=False)
    # Найти python3XX._pth (например python312._pth для 3.12.0)
    parts = version.split(".")
    major_minor = (parts[0] + parts[1]) if len(parts) >= 2 else "311"
    pth_name = f"python{major_minor}._pth"
    pth_path = os.path.join(version_dir, pth_name)
    if os.path.isfile(pth_path):
        with open(pth_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip() for line in f]
        if "Lib/site-packages" not in lines:
            with open(pth_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\nLib/site-packages\n")
            if progress:
                print("  Обновлён ._pth для pip")
    if progress:
        print("  Установка pip")
    subprocess.run(
        [python_exe, get_pip, "--no-warn-script-location"],
        cwd=version_dir,
        capture_output=not progress,
        check=True,
    )
