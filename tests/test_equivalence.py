from itertools import product
from pathlib import Path

import pytest

from src.automaton.determinize import determinize
from src.automaton.equivalence import are_equivalent
from src.automaton.model import Automaton
from src.automaton.parser import parse
from src.automaton.simulator import simulate

FIXTURES = Path(__file__).parent / "fixtures"
BINARY_FIXTURES = [
    "reference_basic", "reference_4th_symbol", "reference_intersection", "reference_personal",
    "4th_symbol_correct", "4th_symbol_buggy", "pdf_example",
]


def _fixture(name: str) -> Automaton:
    return parse((FIXTURES / f"{name}.txt").read_text())


def _same_on_all_words(first: Automaton, second: Automaton, max_length: int = 10) -> bool:
    return all(
        simulate(first, list(word)) == simulate(second, list(word))
        for length in range(max_length + 1)
        for word in product(range(first.m), repeat=length)
    )


def test_different_size_automata_for_same_language_are_equivalent():
    # "Кончается на 1": 2 состояния против 3 (лишнее состояние дублирует финал).
    small = Automaton(n=2, m=2, starts={0}, finals={1},
                      transitions={(0, 0): {0}, (0, 1): {1}, (1, 0): {0}, (1, 1): {1}})
    big = Automaton(n=3, m=2, starts={0}, finals={1, 2},
                    transitions={(0, 0): {0}, (0, 1): {1}, (1, 0): {0}, (1, 1): {2}, (2, 0): {0}, (2, 1): {1}})
    assert are_equivalent(small, big)


def test_nfa_and_its_dfa_are_equivalent():
    nfa = _fixture("reference_4th_symbol")
    assert are_equivalent(nfa, determinize(nfa))


def test_partial_and_complete_dfa_are_equivalent():
    # Только слово "1": частичный DFA и тот же язык с явным sink-состоянием.
    partial = Automaton(n=2, m=2, starts={0}, finals={1}, transitions={(0, 1): {1}})
    complete = Automaton(n=3, m=2, starts={0}, finals={1}, transitions={
        (0, 0): {2}, (0, 1): {1}, (1, 0): {2}, (1, 1): {2}, (2, 0): {2}, (2, 1): {2},
    })
    assert are_equivalent(partial, complete)


def test_buggy_automaton_is_not_equivalent_to_reference():
    assert not are_equivalent(_fixture("4th_symbol_buggy"), _fixture("reference_4th_symbol"))


def test_languages_differing_only_on_empty_word_are_not_equivalent():
    with_empty = Automaton(n=1, m=1, starts={0}, finals={0}, transitions={(0, 0): {0}})
    without_empty = Automaton(n=2, m=1, starts={0}, finals={1}, transitions={(0, 0): {1}, (1, 0): {1}})
    assert not are_equivalent(with_empty, without_empty)


def test_different_alphabet_sizes_are_not_equivalent():
    empty_language_2 = Automaton(n=1, m=2, starts={0}, finals=set(), transitions={})
    empty_language_3 = Automaton(n=1, m=3, starts={0}, finals=set(), transitions={})
    assert not are_equivalent(empty_language_2, empty_language_3)


@pytest.mark.parametrize("first", BINARY_FIXTURES)
@pytest.mark.parametrize("second", BINARY_FIXTURES)
def test_agrees_with_exhaustive_comparison(first, second):
    # Независимая перекрёстная проверка: на всех парах фикстур are_equivalent совпадает с
    # прямым сравнением на всех словах до длины 10 (для этих языков различие, если оно есть,
    # проявляется на коротких словах).
    a, b = _fixture(first), _fixture(second)
    assert are_equivalent(a, b) == _same_on_all_words(a, b)
