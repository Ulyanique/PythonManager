"""Тесты для pyembed.path_env (PATH пользователя на Windows)."""
import os
import sys

import pytest

if sys.platform != "win32":
    pytest.skip("path_env тесты только на Windows", allow_module_level=True)

from pyembed import path_env


@pytest.fixture
def path_value():
    """Текущее значение Path в реестре (сохраняем и восстанавливаем)."""
    try:
        raw = path_env._get_user_path_value()
    except Exception:
        raw = ""
    yield raw
    try:
        path_env._set_user_path_value(raw)
    except Exception:
        pass


@pytest.fixture
def mock_path_value(monkeypatch):
    """Подмена чтения/записи Path: храним значение в списке (один элемент = текущее значение)."""
    storage: list[str] = [""]

    def fake_get() -> str:
        return storage[0]

    def fake_set(value: str) -> None:
        storage[0] = value

    monkeypatch.setattr(path_env, "_get_user_path_value", fake_get)
    monkeypatch.setattr(path_env, "_set_user_path_value", fake_set)
    return storage


def test_get_user_path_entries_empty(mock_path_value):
    """Пустой PATH — пустой список записей."""
    mock_path_value[0] = ""
    assert path_env.get_user_path_entries() == []


def test_get_user_path_entries_normalize(mock_path_value):
    """Записи нормализуются (абсолютные пути)."""
    sep = os.pathsep
    mock_path_value[0] = f"C:\\Foo{sep}D:\\Bar\\baz{sep}"
    entries = path_env.get_user_path_entries()
    assert len(entries) == 2
    assert all(os.path.isabs(e) for e in entries)
    assert "Foo" in entries[0] or "foo" in entries[0].lower()
    assert "Bar" in entries[1] or "bar" in entries[1].lower()


def test_set_user_path_entries(mock_path_value):
    """set_user_path_entries записывает объединённую строку."""
    path_env.set_user_path_entries([r"C:\A", r"D:\B"])
    assert path_env._get_user_path_value() == r"C:\A" + os.pathsep + r"D:\B"


def test_path_add_new(mock_path_value):
    """path_add добавляет новый каталог в начало и возвращает True."""
    mock_path_value[0] = r"C:\Existing"
    added = path_env.path_add(r"D:\New")
    assert added is True
    entries = path_env.get_user_path_entries()
    assert len(entries) == 2
    assert path_env._normalize_path(r"D:\New") == entries[0]


def test_path_add_already_present(mock_path_value):
    """path_add при уже существующей записи возвращает False и не меняет порядок."""
    p = path_env._normalize_path(r"C:\First")
    mock_path_value[0] = p + os.pathsep + path_env._normalize_path(r"D:\Second")
    added = path_env.path_add(r"C:\First")
    assert added is False
    entries = path_env.get_user_path_entries()
    assert entries[0] == p


def test_path_remove_existing(mock_path_value):
    """path_remove удаляет запись и возвращает True."""
    a, b = path_env._normalize_path(r"C:\A"), path_env._normalize_path(r"D:\B")
    mock_path_value[0] = a + os.pathsep + b
    removed = path_env.path_remove(r"C:\A")
    assert removed is True
    assert path_env.get_user_path_entries() == [b]


def test_path_remove_absent(mock_path_value):
    """path_remove при отсутствии записи возвращает False."""
    mock_path_value[0] = path_env._normalize_path(r"C:\Only")
    removed = path_env.path_remove(r"D:\NotThere")
    assert removed is False
    assert len(path_env.get_user_path_entries()) == 1


def test_path_contains(mock_path_value):
    """path_contains возвращает True только если каталог в PATH."""
    mock_path_value[0] = path_env._normalize_path(r"C:\InPath")
    assert path_env.path_contains(r"C:\InPath") is True
    assert path_env.path_contains(r"C:\NotInPath") is False


def test_path_remove_duplicates_with_dups(mock_path_value):
    """path_remove_duplicates убирает дубликаты, сохраняет порядок, возвращает число удалённых."""
    a = path_env._normalize_path(r"C:\A")
    b = path_env._normalize_path(r"D:\B")
    mock_path_value[0] = a + os.pathsep + b + os.pathsep + a + os.pathsep + b
    n = path_env.path_remove_duplicates()
    assert n == 2
    assert path_env.get_user_path_entries() == [a, b]


def test_path_remove_duplicates_no_dups(mock_path_value):
    """path_remove_duplicates при отсутствии дубликатов возвращает 0 и не меняет PATH."""
    a = path_env._normalize_path(r"C:\A")
    b = path_env._normalize_path(r"D:\B")
    mock_path_value[0] = a + os.pathsep + b
    n = path_env.path_remove_duplicates()
    assert n == 0
    assert path_env.get_user_path_entries() == [a, b]
