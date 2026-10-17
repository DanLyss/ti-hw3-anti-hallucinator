from itertools import product
from pathlib import Path

import pytest

from src.automaton.determinize import determinize
from src.automaton.minimize import minimize, minimize_to_file
from src.automaton.model import Automaton
from src.automaton.parser import parse
from src.automaton.serializer import to_text
from src.automaton.simulator import simulate
from src.testcases import TESTCASES

FIXTURES = Path(__file__).parent / "fixtures"
REFERENCES = ["basic", "4th_symbol", "intersection", "personal", "employer"]


def _reference(name: str) -> Automaton:
    return parse((FIXTURES / f"reference_{name}.txt").read_text())


def test_ends_with_one_hand_computed():
    # "Слово кончается на 1": 0 -1-> 1 -1-> 2 -1-> 1, по 0 из любого — в 0, финалы {1, 2}.
    # Вручную: R0={0}, R1={1,2}; по 0 из R1 оба в R0, по 1 оба в R1 — делить нечего,
    # 1 и 2 склеиваются: 2 состояния.
    dfa = Automaton(
        n=3, m=2, starts={0}, finals={1, 2},
        transitions={(0, 0): {0}, (0, 1): {1}, (1, 0): {0}, (1, 1): {2}, (2, 0): {0}, (2, 1): {1}},
    )
    minimal = minimize(dfa)
    assert minimal.n == 2
    assert minimal.finals == {1}
    assert minimal.transitions == {(0, 0): {0}, (0, 1): {1}, (1, 0): {0}, (1, 1): {1}}


def test_split_needs_several_rounds_hand_computed():
    # Цепочка 0 -a-> 1 -a-> 2 -a-> 3 (финал), 3 -a-> 3. Вручную:
    # R0={0,1,2}, R1={3}; по a: 2 уходит в R1, 0 и 1 — в R0 -> {0,1}, {2}, {3};
    # затем 1 уходит в {2}, 0 — в {0,1} -> {0}, {1}, {2}, {3}. Всё различимо: 4 состояния.
    dfa = Automaton(n=4, m=1, starts={0}, finals={3},
                    transitions={(0, 0): {1}, (1, 0): {2}, (2, 0): {3}, (3, 0): {3}})
    assert minimize(dfa).n == 4


def test_unreachable_states_are_removed_first():
    # Состояние 2 недостижимо и само по себе ни с кем не эквивалентно (финал без переходов).
    dfa = Automaton(n=3, m=1, starts={0}, finals={2}, transitions={(0, 0): {1}, (1, 0): {0}})
    minimal = minimize(dfa)
    assert minimal.n == 1
    assert minimal.finals == set()


def test_partial_dfa_is_completed_with_sink():
    # Только слово "1": 0 -1-> 1, остальных переходов нет. Полный минимальный DFA:
    # старт, финал и sink (по 0 из старта и по любому символу из финала).
    dfa = Automaton(n=2, m=2, starts={0}, finals={1}, transitions={(0, 1): {1}})
    minimal = minimize(dfa)
    assert minimal.n == 3
    assert all((q, a) in minimal.transitions for q in range(3) for a in range(2))


def test_empty_and_full_language_give_one_state():
    no_finals = Automaton(n=2, m=2, starts={0}, finals=set(),
                          transitions={(0, 0): {1}, (0, 1): {0}, (1, 0): {1}, (1, 1): {0}})
    all_finals = Automaton(n=2, m=2, starts={0}, finals={0, 1},
                           transitions={(0, 0): {1}, (0, 1): {0}, (1, 0): {1}, (1, 1): {0}})
    assert minimize(no_finals).n == 1 and minimize(no_finals).finals == set()
    assert minimize(all_finals).n == 1 and minimize(all_finals).finals == {0}


def test_nfa_is_rejected():
    nfa = Automaton(n=2, m=1, starts={0}, finals={1}, transitions={(0, 0): {0, 1}})
    with pytest.raises(ValueError):
        minimize(nfa)


def test_fourth_symbol_gives_exactly_16_states():
    # 2^4: по Майхиллу–Нероуду все 16 вариантов последних четырёх символов различимы.
    assert minimize(determinize(_reference("4th_symbol"))).n == 16


@pytest.mark.parametrize("name", REFERENCES)
def test_minimization_preserves_language(name):
    original = _reference(name)
    minimal = minimize(determinize(original))
    testcase = TESTCASES[name.replace("_", "-")]
    alphabet = ("A", "S", "P", "B", "0", "1") if name == "employer" else testcase.alphabet
    max_length = 8 if name == "employer" else 10
    for length in range(max_length + 1):
        for word in map("".join, product(alphabet, repeat=length)):
            encoded = testcase.encode(word)
            assert simulate(minimal, encoded) == simulate(original, encoded), word


@pytest.mark.parametrize("name", REFERENCES)
def test_minimization_is_idempotent(name):
    minimal = minimize(determinize(_reference(name)))
    assert minimize(minimal) == minimal


def test_minimize_to_file_writes_parseable_automaton(tmp_path):
    out = tmp_path / "minimal" / "4th_symbol.txt"
    minimal = minimize_to_file(_reference("4th_symbol"), out)  # NFA на входе — детерминизируется
    assert out.read_text(encoding="utf-8") == to_text(minimal)
    assert parse(out.read_text(encoding="utf-8")) == minimal


def test_lecture_example_1():
    # Пример 1 лекции 4 (рис. 2–3): 6 состояний над {a, b} (a = 0, b = 1), язык |w|_a ≡ 0 (mod 3).
    # q5 недостижимо; R0 = {q2, q3, q4}, R1 = {q0, q1}; R0 расщепляется по a на {q2, q3} и {q4} —
    # минимальный автомат из 3 состояний: {q0, q1} -a-> {q2, q3} -a-> {q4} -a-> {q0, q1}, по b — петли.
    a, b = 0, 1
    dfa = Automaton(n=6, m=2, starts={0}, finals={0, 1}, transitions={
        (0, b): {1}, (1, b): {0}, (0, a): {2}, (1, a): {3},
        (2, b): {3}, (2, a): {4}, (3, b): {3}, (3, a): {4},
        (4, b): {4}, (4, a): {1}, (5, b): {5}, (5, a): {2},
    })
    minimal = minimize(dfa)
    assert minimal.n == 3
    assert minimal.finals == {0}
    assert minimal.transitions == {
        (0, a): {1}, (0, b): {0}, (1, a): {2}, (1, b): {1}, (2, a): {0}, (2, b): {2},
    }
