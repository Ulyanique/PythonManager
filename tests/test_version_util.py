"""Тесты для pyembed.version_util."""
import pytest

from pyembed.version_util import version_sort_key


def test_version_sort_key_stable():
    """Стабильные версии: (major, minor, micro, 3, 0)."""
    assert version_sort_key("3.12.0") == (3, 12, 0, 3, 0)
    assert version_sort_key("3.14.3") == (3, 14, 3, 3, 0)


def test_version_sort_key_alpha():
    """Alpha: stage=0."""
    assert version_sort_key("3.15.0a4") == (3, 15, 0, 0, 4)
    assert version_sort_key("3.15.0a1") == (3, 15, 0, 0, 1)


def test_version_sort_key_beta_rc():
    """Beta и rc."""
    assert version_sort_key("3.12.0b1") == (3, 12, 0, 1, 1)
    assert version_sort_key("3.12.0rc2") == (3, 12, 0, 2, 2)


def test_version_sort_key_ordering():
    """Порядок: новый стабильный > alpha > старый стабильный > rc (стабильный выше rc)."""
    versions = ["3.12.0", "3.15.0a4", "3.14.3", "3.12.0rc1", "3.15.0"]
    sorted_desc = sorted(versions, key=version_sort_key, reverse=True)
    assert sorted_desc[0] == "3.15.0"
    assert sorted_desc[1] == "3.15.0a4"
    assert sorted_desc[2] == "3.14.3"
    assert sorted_desc[3] == "3.12.0"
    assert sorted_desc[4] == "3.12.0rc1"


def test_version_sort_key_unknown():
    """Неверный формат даёт (0,0,0,0,0)."""
    assert version_sort_key("") == (0, 0, 0, 0, 0)
    assert version_sort_key("abc") == (0, 0, 0, 0, 0)
