"""Тесты для pyembed.local."""
import os
import tempfile
from pathlib import Path

import pytest

from pyembed.local import (
    get_python_exe,
    get_version_dir,
    has_pip,
    list_installed,
    uninstall_version,
)


@pytest.fixture
def root_dir(tmp_path):
    """Временный корень с несколькими «версиями»."""
    for ver in ("3.12.0", "3.14.3", "3.15.0a4"):
        d = tmp_path / ver
        d.mkdir()
        (d / "python.exe").touch()
    # Версия без python.exe — не должна попасть в список
    (tmp_path / "3.11.0").mkdir()
    return str(tmp_path)


def test_list_installed(root_dir):
    """list_installed возвращает только каталоги с python.exe, отсортированы по убыванию."""
    got = list_installed(root_dir)
    assert set(got) == {"3.12.0", "3.14.3", "3.15.0a4"}
    assert got[0] == "3.15.0a4"
    assert got[-1] == "3.12.0"


def test_list_installed_empty(tmp_path):
    """Пустой или несуществующий каталог — пустой список."""
    assert list_installed(str(tmp_path)) == []
    assert list_installed(str(tmp_path / "nonexistent")) == []


def test_get_python_exe(root_dir):
    """get_python_exe возвращает путь к exe или None."""
    exe = get_python_exe(root_dir, "3.12.0")
    assert exe is not None
    assert exe.endswith(os.path.join("3.12.0", "python.exe"))
    assert os.path.isfile(exe)
    assert get_python_exe(root_dir, "3.99.0") is None


def test_get_version_dir(root_dir):
    """get_version_dir — путь к каталогу версии."""
    assert get_version_dir(root_dir, "3.12.0") == os.path.join(root_dir, "3.12.0")


def test_has_pip_false(root_dir):
    """Без Lib/site-packages pip нет."""
    assert has_pip(root_dir, "3.12.0") is False


def test_has_pip_true(root_dir):
    """С pip в site-packages — True."""
    site = Path(root_dir) / "3.12.0" / "Lib" / "site-packages"
    site.mkdir(parents=True)
    (site / "pip").mkdir()
    (site / "pip" / "__init__.py").touch()
    assert has_pip(root_dir, "3.12.0") is True


def test_uninstall_version(root_dir):
    """uninstall_version удаляет каталог версии."""
    ver_dir = os.path.join(root_dir, "3.15.0a4")
    assert os.path.isdir(ver_dir)
    result = uninstall_version(root_dir, "3.15.0a4")
    assert result is True
    assert not os.path.isdir(ver_dir)
    assert uninstall_version(root_dir, "3.99.0") is False
