"""Сортировка и разбор версий Python (в т.ч. 3.15.0a4, 3.12.0)."""
import re


def version_sort_key(version_str: str) -> tuple[int, int, int, int, int]:
    """
    Ключ для сортировки: (major, minor, micro, stage, stage_num).
    stage: 0=alpha, 1=beta, 2=rc, 3=final.
    При reverse=True получаем порядок от новых к старым.
    """
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", version_str.strip())
    if not m:
        return (0, 0, 0, 0, 0)
    major, minor, micro = int(m.group(1)), int(m.group(2)), int(m.group(3))
    suffix = (m.group(4) or "").lower()
    if not suffix:
        return (major, minor, micro, 3, 0)
    num_match = re.search(r"\d+", suffix)
    stage_num = int(num_match.group()) if num_match else 0
    if suffix.startswith("a") or "alpha" in suffix:
        return (major, minor, micro, 0, stage_num)
    if suffix.startswith("b") or "beta" in suffix:
        return (major, minor, micro, 1, stage_num)
    if suffix.startswith("rc") or (suffix.startswith("c") and len(suffix) > 1):
        return (major, minor, micro, 2, stage_num)
    return (major, minor, micro, 3, 0)
