from collections import deque
from dataclasses import dataclass
from typing import Callable, Hashable

from src.automaton.minimize import minimize
from src.automaton.model import Automaton


@dataclass
class TwoWayTestCase:
    id: str
    description: str  # ровно текст из таблички листка, математика — в TeX
    alphabet: tuple[str, ...]
    ground_truth: Callable[[str], bool]

    def encode(self, word: str) -> list[int]:
        return [self.alphabet.index(ch) for ch in word]


def _basic_ground_truth(w: str) -> bool:
    # (0|1)^*0(0|1)^{12}: 13-й символ с конца — 0. В табличке листка звёздочка потерялась
    # при вёрстке TeX, преподаватель подтвердил исправленный вариант.
    return len(w) >= 13 and w[-13] == "0"


def _grob_ground_truth(w: str) -> bool:
    # L = {w | ww ∈ L(A)}, L(A) — строки без подстроки 110
    return "110" not in w + w


TESTCASES_2DFA: dict[str, TwoWayTestCase] = {
    "2dfa_basic": TwoWayTestCase(
        id="2dfa_basic",
        description=r"Язык (0|1)^*0(0|1)^{12}, алфавит \{0 , 1\}",
        alphabet=("0", "1"),
        ground_truth=_basic_ground_truth,
    ),
    "2dfa_grob": TwoWayTestCase(
        id="2dfa_grob",
        description=(
            r"L = \{w \mid ww \in L(A)\}, где L(A) — язык всех строк над алфавитом \{0 , 1\}, "
            r"где не содержится подстроки 110"
        ),
        alphabet=("0", "1"),
        ground_truth=_grob_ground_truth,
    ),
}


def _dfa_from_summary(m: int, init: Hashable, step: Callable, accept: Callable) -> Automaton:
    """DFA BFS-ом по "сводкам" префикса: состояние — step-образ прочитанного префикса."""
    index = {init: 0}
    queue = deque([init])
    transitions: dict[tuple[int, int], set[int]] = {}
    while queue:
        summary = queue.popleft()
        for symbol in range(m):
            target = step(summary, symbol)
            if target not in index:
                index[target] = len(index)
                queue.append(target)
            transitions[(index[summary], symbol)] = {index[target]}
    finals = {i for summary, i in index.items() if accept(summary)}
    return Automaton(n=len(index), m=m, starts={0}, finals=finals, transitions=transitions)


# DFA для A = "нет подстроки 110": 0 — последний символ не 1, 1 — ровно одна 1 на конце,
# 2 — на конце 11, 3 — мёртвое (110 встретилась).
_A_DELTA = {(0, 0): 0, (0, 1): 1, (1, 0): 0, (1, 1): 2, (2, 0): 3, (2, 1): 2, (3, 0): 3, (3, 1): 3}


def ground_truth_min_dfa(testcase_id: str) -> Automaton:
    """Минимальный DFA для тесткейса. basic: сводка — последние 13 символов как 13-битное
    число (короткое слово дополнено единицами слева: «13-го с конца нет» ≡ «он не 0»),
    ровно 2^13 = 8192 состояний;
    grob: сводка — функция переходов A на прочитанном префиксе w (g: Q_A -> Q_A), тогда
    ww ∈ L(A) ⟺ g(g(0)) не мёртвое."""
    if testcase_id == "2dfa_basic":
        window = (1 << 13) - 1
        dfa = _dfa_from_summary(
            2, window,
            lambda s, c: ((s << 1) | c) & window,
            lambda s: not s >> 12,  # старший бит окна — 13-й символ с конца — равен 0
        )
    elif testcase_id == "2dfa_grob":
        dfa = _dfa_from_summary(
            2, (0, 1, 2, 3),
            lambda g, c: tuple(_A_DELTA[(g[q], c)] for q in range(4)),
            lambda g: g[g[0]] != 3,
        )
    else:
        raise KeyError(testcase_id)
    return minimize(dfa)
