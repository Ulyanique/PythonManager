"""Тесты для pyembed.config (get/set default version, recent versions)."""
import os
import tempfile

import pytest

from pyembed.config import (
    DEFAULT_VERSION_FILE,
    add_recent_version,
    get_default_version,
    get_recent_versions,
    get_root,
    set_default_version,
)


def test_get_default_version_empty(tmp_path):
    """Без файла — None."""
    assert get_default_version(str(tmp_path)) is None


def test_set_and_get_default_version(tmp_path):
    """Запись и чтение версии по умолчанию."""
    set_default_version(str(tmp_path), "3.12.0")
    assert get_default_version(str(tmp_path)) == "3.12.0"
    path = tmp_path / DEFAULT_VERSION_FILE
    assert path.read_text(encoding="utf-8").strip() == "3.12.0"


def test_set_default_version_strips(tmp_path):
    """Пробелы в версии обрезаются при записи."""
    set_default_version(str(tmp_path), "  3.14.3\n")
    assert get_default_version(str(tmp_path)) == "3.14.3"


def test_recent_versions_empty(tmp_path):
    """Без файла — пустой список."""
    assert get_recent_versions(str(tmp_path)) == []


def test_add_recent_version(tmp_path):
    """Добавление и чтение недавних версий."""
    root = str(tmp_path)
    add_recent_version(root, "3.12.0")
    assert get_recent_versions(root) == ["3.12.0"]
    add_recent_version(root, "3.14.3")
    assert get_recent_versions(root) == ["3.14.3", "3.12.0"]
    add_recent_version(root, "3.12.0")
    assert get_recent_versions(root) == ["3.12.0", "3.14.3"]
