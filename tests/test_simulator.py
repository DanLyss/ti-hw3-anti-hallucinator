from pathlib import Path

import pytest

from src.automaton.parser import parse
from src.automaton.simulator import check_correctness, simulate
from src.testcases import TESTCASES

FIXTURES = Path(__file__).parent / "fixtures"


def _pdf_automaton():
    return parse((FIXTURES / "pdf_example.txt").read_text())


@pytest.mark.parametrize(
    "word,expected",
    [
        ([], False),
        ([0], True),
        ([1], False),
        ([0, 0], False),
        ([0, 1], False),
        ([1, 0], False),
        ([1, 0, 0], True),
    ],
)
def test_simulate_on_pdf_example(word, expected):
    # Ручная трассировка автомата из ПДФ (n=3, start={0}, final={1}) — см. комментарий
    # в PLAN.md/коммите: посчитано вручную по transitions из tests/fixtures/pdf_example.txt.
    assert simulate(_pdf_automaton(), word) == expected


def test_check_correctness_true_for_correct_automaton():
    automaton = parse((FIXTURES / "4th_symbol_correct.txt").read_text())
    testcase = TESTCASES["4th-symbol"]
    samples = [(testcase.encode(w), label) for w, label in testcase.sample_strings()]
    assert check_correctness(automaton, samples)


def test_check_correctness_false_for_buggy_automaton():
    automaton = parse((FIXTURES / "4th_symbol_buggy.txt").read_text())
    testcase = TESTCASES["4th-symbol"]
    samples = [(testcase.encode(w), label) for w, label in testcase.sample_strings()]
    assert not check_correctness(automaton, samples)
