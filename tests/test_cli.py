"""Тесты CLI (вызов команд)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Корень проекта (родитель tests/)
ROOT = Path(__file__).resolve().parent.parent


def run_pyembed(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Запуск pyembed через python -m pyembed."""
    cmd = [sys.executable, "-m", "pyembed", *args]
    run_env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        env=run_env,
    )


def test_cli_list_exit_zero():
    """pyembed list завершается с 0."""
    r = run_pyembed("list")
    assert r.returncode == 0
    assert "Установленные" in r.stdout or "установленных" in r.stdout or "нет" in r.stdout


def test_cli_list_available_exit_zero():
    """pyembed list -a может завершиться 0 (при сети) или ненулем (без сети)."""
    r = run_pyembed("list", "--available")
    # Либо успех, либо сетевая ошибка — оба допустимы в тестах
    assert r.returncode in (0, 1)


def test_cli_help():
    """pyembed --help и pyembed list --help."""
    r = run_pyembed("--help")
    assert r.returncode == 0
    assert "pyembed" in r.stdout and "install" in r.stdout
    r2 = run_pyembed("list", "--help")
    assert r2.returncode == 0
    assert "available" in r2.stdout or "установленные" in r2.stdout.lower()


def test_cli_verify_missing_version():
    """pyembed verify несуществующей версии — код 1."""
    r = run_pyembed("verify", "99.99.99")
    assert r.returncode == 1
    # Сообщение об ошибке в stderr (кодировка может отличаться)
    assert "99.99.99" in r.stderr or "not found" in r.stderr.lower() or len(r.stderr) > 50


def test_cli_cache_list_exit_zero():
    """pyembed cache list завершается с 0."""
    r = run_pyembed("cache", "list")
    assert r.returncode == 0
    assert "Кэш" in r.stdout or "пуст" in r.stdout or "МБ" in r.stdout


def test_cli_info_missing_version():
    """pyembed info несуществующей версии — код 1."""
    r = run_pyembed("info", "99.99.99")
    assert r.returncode == 1
    assert "99.99.99" in r.stderr or "не установлена" in r.stderr


def test_cli_upgrade_pip_missing_version():
    """pyembed upgrade-pip несуществующей версии — код 1."""
    r = run_pyembed("upgrade-pip", "99.99.99")
    assert r.returncode == 1
    assert "99.99.99" in r.stderr or "не установлена" in r.stderr


def test_cli_which_missing_version():
    """pyembed which несуществующей версии — код 1."""
    r = run_pyembed("which", "99.99.99")
    assert r.returncode == 1
    assert "99.99.99" in r.stderr or "не установлена" in r.stderr


def test_cli_verify_installed_version(tmp_path):
    """pyembed verify установленной версии (минимальный каталог) — код 0."""
    version_dir = tmp_path / "3.12.0"
    version_dir.mkdir()
    (version_dir / "python.exe").write_bytes(b"")
    (version_dir / "python312.dll").write_bytes(b"")
    env = {"PYEMBED_ROOT": str(tmp_path)}
    r = run_pyembed("verify", "3.12.0", env=env)
    assert r.returncode == 0
    assert "всё на месте" in r.stdout or "3.12.0" in r.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="path fix-duplicates только на Windows")
def test_cli_path_fix_duplicates():
    """pyembed path fix-duplicates на Windows завершается с 0 и выводит сообщение о дубликатах или их отсутствии."""
    r = run_pyembed("path", "fix-duplicates")
    assert r.returncode == 0
    out = (r.stdout + r.stderr).lower()
    assert "дубликат" in out or "path" in out
