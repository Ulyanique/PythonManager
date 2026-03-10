"""Тесты для pyembed.download (embed_url, _parse_ftp_listing, кэш, целостность zip)."""
import re
import zipfile

import pytest

from pyembed.download import (
    BASE_FTP,
    _parse_ftp_listing,
    _version_base_path,
    check_zip_integrity,
    clear_cache,
    embed_url,
    get_cache_dir,
    list_cache,
)


def test_version_base_path():
    """Базовый путь для pre-release — первые три компонента."""
    assert _version_base_path("3.12.0") == "3.12.0"
    assert _version_base_path("3.15.0a4") == "3.15.0"
    assert _version_base_path("3.12.0rc1") == "3.12.0"


def test_embed_url_stable():
    """URL стабильной версии: каталог и файл с той же версией."""
    url = embed_url("3.12.0", arch="amd64")
    assert url == f"{BASE_FTP}/3.12.0/python-3.12.0-embed-amd64.zip"


def test_embed_url_prerelease():
    """URL pre-release: каталог — база (3.15.0), файл — полная версия (3.15.0a4)."""
    url = embed_url("3.15.0a4", arch="amd64")
    assert url == f"{BASE_FTP}/3.15.0/python-3.15.0a4-embed-amd64.zip"


def test_embed_url_arch():
    """Разные архитектуры в имени файла."""
    assert "win32" in embed_url("3.12.0", arch="win32")
    assert "arm64" in embed_url("3.12.0", arch="arm64")


def test_parse_ftp_listing():
    """Из HTML извлекаются версии и pre-release, сортировка по убыванию."""
    html = '''
    <a href="3.12.0/">3.12.0/</a>
    <a href="3.14.3/">3.14.3/</a>
    <a href="3.15.0a4/">3.15.0a4/</a>
    <a href="2.7.18/">2.7.18/</a>
    '''
    versions = _parse_ftp_listing(html)
    assert "3.12.0" in versions
    assert "3.14.3" in versions
    assert "3.15.0a4" in versions
    assert "2.7.18" in versions
    assert versions[0] == "3.15.0a4"
    assert versions[-1] == "2.7.18"


def test_parse_ftp_listing_dedup():
    """Дубликаты не добавляются."""
    html = '<a href="3.12.0/">3.12.0/</a><a href="3.12.0/">3.12.0/</a>'
    versions = _parse_ftp_listing(html)
    assert versions.count("3.12.0") == 1


def test_get_cache_dir(tmp_path):
    """Путь к кэшу — root/.cache."""
    cache = get_cache_dir(str(tmp_path))
    assert cache == str(tmp_path / ".cache")


def test_list_cache_empty(tmp_path):
    """Пустой или отсутствующий кэш — пустой список."""
    assert list_cache(str(tmp_path)) == []
    (tmp_path / ".cache").mkdir()
    assert list_cache(str(tmp_path)) == []


def test_list_cache_with_files(tmp_path):
    """list_cache возвращает имя и размер файлов в .cache."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    (cache_dir / "python-3.12.0-embed-amd64.zip").write_bytes(b"x" * 100)
    (cache_dir / "python-3.11.0-embed-amd64.zip").write_bytes(b"y" * 200)
    items = list_cache(str(tmp_path))
    assert len(items) == 2
    names = [x[0] for x in items]
    assert "python-3.12.0-embed-amd64.zip" in names
    assert "python-3.11.0-embed-amd64.zip" in names
    sizes = {x[0]: x[1] for x in items}
    assert sizes["python-3.12.0-embed-amd64.zip"] == 100
    assert sizes["python-3.11.0-embed-amd64.zip"] == 200


def test_clear_cache_all(tmp_path):
    """clear_cache без version удаляет все файлы в кэше."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    (cache_dir / "a.zip").write_bytes(b"a")
    (cache_dir / "b.zip").write_bytes(b"b")
    n = clear_cache(str(tmp_path), None)
    assert n == 2
    assert list_cache(str(tmp_path)) == []


def test_clear_cache_version(tmp_path):
    """clear_cache(version) удаляет только файлы, содержащие версию в имени."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    (cache_dir / "python-3.12.0-embed-amd64.zip").write_bytes(b"a")
    (cache_dir / "python-3.11.0-embed-amd64.zip").write_bytes(b"b")
    n = clear_cache(str(tmp_path), "3.12.0")
    assert n == 1
    items = list_cache(str(tmp_path))
    assert len(items) == 1
    assert "3.11.0" in items[0][0]


def test_check_zip_integrity_valid(tmp_path):
    """Валидный zip проходит проверку."""
    zip_path = tmp_path / "good.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("a.txt", b"hello")
    check_zip_integrity(str(zip_path))
    assert zip_path.exists()


def test_check_zip_integrity_not_zip(tmp_path):
    """Не-zip файл вызывает OSError и файл удаляется."""
    bad_path = tmp_path / "bad.zip"
    bad_path.write_bytes(b"not a zip")
    with pytest.raises(OSError, match="zip|повреждён"):
        check_zip_integrity(str(bad_path))
    assert not bad_path.exists()
