from itertools import product
from pathlib import Path

import pytest

from src.automaton.parser import parse
from src.automaton.simulator import simulate
from src.pipeline.evaluator import evaluate_file
from src.testcases import TESTCASES

FIXTURES = Path(__file__).parent / "fixtures"

# Контрольный эксперимент: заведомо правильные автоматы (построены руками) для всех 5 тесткейсов.
# Если пайплайн оценки исправен, каждый должен пройти все проверки — так почти 0% корректных
# у моделей в итоговой таблице нельзя списать на баг в оценке.
# testcase -> (детерминированный ли эталон, ожидаемое число состояний DFA после determinize)
REFERENCE = {
    "basic": (True, 10),
    "4th-symbol": (False, 16),  # NFA на 5 состояний -> DFA ровно на 2^4 = 16 (минимум по Майхиллу–Нероуду)
    "intersection": (True, 20),
    "personal": (True, 3),
    "employer": (True, 12),
}


def _fixture(testcase_id: str) -> Path:
    return FIXTURES / f"reference_{testcase_id.replace('-', '_')}.txt"


@pytest.mark.parametrize("testcase_id", sorted(REFERENCE))
def test_reference_automaton_passes_all_checks(testcase_id):
    expected_deterministic, expected_dfa_states = REFERENCE[testcase_id]

    result = evaluate_file("reference", testcase_id, "000", _fixture(testcase_id))

    assert result.is_format_valid is True
    assert result.is_deterministic is expected_deterministic
    assert result.dfa_state_count == expected_dfa_states
    assert result.is_simulation_correct is True


@pytest.mark.parametrize("testcase_id", sorted(REFERENCE))
def test_reference_automaton_matches_ground_truth_exhaustively(testcase_id):
    """Не только на выборке sample_strings(), а на всех словах до фиксированной длины —
    независимая проверка, что совпадение с ground truth не случайность маленькой выборки."""
    testcase = TESTCASES[testcase_id]
    automaton = parse(_fixture(testcase_id).read_text(encoding="utf-8"))
    if testcase_id == "employer":
        # полный алфавит из 12 символов до длины 8 — это ~4.7e8 слов; берём представителей
        # каждого класса: буква из SPB, буква вне SPB, ноль, ненулевая цифра
        alphabet, max_length = ("A", "S", "P", "B", "0", "1"), 8
    else:
        alphabet, max_length = testcase.alphabet, 10

    mismatches = [
        word
        for length in range(max_length + 1)
        for word in map("".join, product(alphabet, repeat=length))
        if simulate(automaton, testcase.encode(word)) != testcase.ground_truth(word)
    ]

    assert mismatches == []
