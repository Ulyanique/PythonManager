"""Тесты для pyembed.local (verify_version)."""
import os
from pathlib import Path

import pytest

from pyembed.local import verify_version


def test_verify_version_ok(tmp_path):
    """Полная версия — ok."""
    (tmp_path / "3.12.0").mkdir()
    (tmp_path / "3.12.0" / "python.exe").touch()
    (tmp_path / "3.12.0" / "python312.dll").touch()
    ok, missing = verify_version(str(tmp_path), "3.12.0")
    assert ok is True
    assert missing == []


def test_verify_version_missing_dir(tmp_path):
    """Каталога нет."""
    ok, missing = verify_version(str(tmp_path), "3.99.0")
    assert ok is False
    assert len(missing) == 1
    assert "не найден" in missing[0] or "3.99.0" in missing[0]


def test_verify_version_missing_exe(tmp_path):
    """Каталог есть, python.exe нет."""
    (tmp_path / "3.12.0").mkdir()
    ok, missing = verify_version(str(tmp_path), "3.12.0")
    assert ok is False
    assert "python.exe" in missing


def test_verify_version_prerelease(tmp_path):
    """Pre-release: python315.dll для 3.15.0a4."""
    (tmp_path / "3.15.0a4").mkdir()
    (tmp_path / "3.15.0a4" / "python.exe").touch()
    (tmp_path / "3.15.0a4" / "python315.dll").touch()
    ok, missing = verify_version(str(tmp_path), "3.15.0a4")
    assert ok is True
    assert missing == []
