from pathlib import Path

import pytest

from src.automaton.determinize import TooManyStatesError, determinize
from src.automaton.model import Automaton
from src.automaton.parser import parse
from src.automaton.simulator import check_correctness, simulate
from src.testcases import TESTCASES

FIXTURES = Path(__file__).parent / "fixtures"


def test_simple_two_state_nfa_hand_computed():
    # NFA: 2 состояния, 1 символ, (0,0)->{0,1}. Финал={1}.
    # Вручную: S0={0} (индекс0, не финал) --0--> S1={0,1} (индекс1, финал, self-loop на 0).
    # Подмножества {} и {1} никогда не достижимы от старта и не должны попасть в DFA.
    nfa = Automaton(n=2, m=1, starts={0}, finals={1}, transitions={(0, 0): {0, 1}})
    dfa = determinize(nfa)
    assert dfa.n == 2
    assert dfa.starts == {0}
    assert dfa.finals == {1}
    assert dfa.transitions == {(0, 0): {1}, (1, 0): {1}}


def test_pdf_example_hand_computed():
    # Подмножества посчитаны вручную (см. коммит Этапа 3):
    # S0={0}, S1={1,2}, S2={2}, S3={0,2}, S4={0,1,2} — ровно 5 достижимых подмножеств
    # из 2^3=8 возможных ({} и {1} по отдельности не достижимы).
    nfa = parse((FIXTURES / "pdf_example.txt").read_text())
    dfa = determinize(nfa)
    assert dfa.n == 5
    assert dfa.starts == {0}
    assert dfa.finals == {1, 4}
    assert dfa.transitions == {
        (0, 0): {1},
        (0, 1): {2},
        (1, 0): {3},
        (1, 1): {2},
        (2, 0): {0},
        (2, 1): {2},
        (3, 0): {4},
        (3, 1): {2},
        (4, 0): {4},
        (4, 1): {2},
    }


def test_dfa_accepts_same_language_as_original_nfa():
    nfa = parse((FIXTURES / "4th_symbol_correct.txt").read_text())
    dfa = determinize(nfa)
    testcase = TESTCASES["4th-symbol"]
    samples = [(testcase.encode(w), label) for w, label in testcase.sample_strings()]
    assert check_correctness(nfa, samples)
    assert check_correctness(dfa, samples)
    for word, _ in samples:
        assert simulate(nfa, word) == simulate(dfa, word)


def test_no_transitions_added_for_empty_target_subset():
    # (0,0) никуда не ведёт -> переход не должен появиться в DFA вовсе (не sink-состояние).
    nfa = Automaton(n=1, m=1, starts={0}, finals=set(), transitions={})
    dfa = determinize(nfa)
    assert dfa.n == 1
    assert dfa.transitions == {}
    assert dfa.finals == set()


def test_empty_start_set_gives_single_dead_state():
    nfa = Automaton(n=2, m=2, starts=set(), finals={0}, transitions={(0, 0): {1}})
    dfa = determinize(nfa)
    assert dfa.n == 1
    assert dfa.finals == set()
    assert dfa.transitions == {}


def test_raises_when_exceeding_max_states():
    # Обобщение фикстуры 4th_symbol_correct.txt (k-й символ с конца): NFA из k+1 состояний,
    # минимальный DFA для неё требует ровно 2^k состояний (классический пример
    # экспоненциального взрыва при детерминизации). При k=5 это 32 — ловим раньше предела.
    k = 5
    transitions = {(0, 0): {0}, (0, 1): {0, 1}}
    for i in range(1, k):
        transitions[(i, 0)] = {i + 1}
        transitions[(i, 1)] = {i + 1}
    nfa = Automaton(n=k + 1, m=2, starts={0}, finals={k}, transitions=transitions)
    with pytest.raises(TooManyStatesError):
        determinize(nfa, max_states=10)


def test_deterministic_input_drops_unreachable_states_only():
    # DFA из 4 состояний, состояние 3 недостижимо (в него никто не ведёт), финал={3,1}.
    # Ожидаем тот же автомат на 3 состояниях: 0 -0-> 1 -1-> 2, финальным остаётся только 1.
    dfa_in = Automaton(
        n=4, m=2, starts={0}, finals={1, 3},
        transitions={(0, 0): {1}, (1, 1): {2}, (2, 0): {0}, (3, 0): {0}},
    )
    dfa = determinize(dfa_in)
    assert dfa.n == 3
    assert dfa.starts == {0}
    assert dfa.finals == {1}
    assert dfa.transitions == {(0, 0): {1}, (1, 1): {2}, (2, 0): {0}}


def test_deterministic_input_gives_same_result_as_subset_construction(monkeypatch):
    # Ранний выход для DFA не должен ничего менять по сравнению с честным построением
    # подмножеств: проверяем на эталонных DFA всех тесткейсов с отключённым ранним выходом.
    import src.automaton.determinize as det

    for name in ["basic", "intersection", "personal", "employer"]:
        dfa_in = parse((FIXTURES / f"reference_{name}.txt").read_text())
        fast = determinize(dfa_in)
        with monkeypatch.context() as m:
            m.setattr(det, "is_deterministic", lambda _: False)
            slow = determinize(dfa_in)
        assert fast == slow, name
