from dataclasses import dataclass
from typing import Callable


@dataclass
class TestCase:
    id: str
    description: str
    alphabet: tuple[str, ...]
    ground_truth: Callable[[str], bool]

    def sample_strings(self) -> list[tuple[str, bool]]:
        """Позитивные/негативные/граничные строки для симулятора. Реализация — Этап 2 (PLAN.md)."""
        raise NotImplementedError


# Тексты описаний — ровно как в табличке ПДФ (см. TCS_2026_hw3.pdf, стр. 2).
# Наполнение (ground_truth, sample_strings) — Этап 2 (PLAN.md).
TESTCASES: dict[str, TestCase] = {}
