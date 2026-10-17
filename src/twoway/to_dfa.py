from collections import deque

from src.automaton.model import Automaton
from src.twoway.model import RIGHT, TwoWayAutomaton
from src.twoway.validator import is_deterministic_two_way

class TooManyStatesError(Exception):
    """Достижимых пар (q̂, f) больше разумного лимита (в худшем случае их n(n^n − (n−1)^n))."""


Behavior = tuple[int | None, ...]  # f: Q -> Q (None — не определено), f[q] для q = 0..n-1
_DEAD = "dead"


def two_way_to_dfa(automaton: TwoWayAutomaton, max_states: int = 20_000) -> Automaton:
    """2DFA -> DFA построением Шепердсона [1959] в варианте из лекции 4 (лемма 1, Капуцис).

    Состояние DFA после чтения u — пара (q̂, f):
      I.  q̂ — состояние, в котором 2DFA, стартовав на ⊢u, впервые уходит направо с последнего символа;
      II. f(q) — в каком состоянии 2DFA уйдёт направо с последнего символа ⊢u, если начнёт на нём
          в состоянии q (None — отвергнет или зациклится).
    Плюс одно мёртвое состояние: 2DFA никогда не уходит направо с ⊢u. Строятся только
    достижимые пары (BFS от старта), а не все n^n функции."""
    if not is_deterministic_two_way(automaton):
        raise ValueError("two_way_to_dfa() преобразует только детерминированные 2DFA")
    n, m = automaton.n, automaton.m
    delta = {key: next(iter(targets)) for key, targets in automaton.transitions.items()}

    # f0 записывает переходы по ⊢ направо; q0' — куда 2DFA впервые выходит с ⊢
    f0: Behavior = tuple(_move_right(delta, q, m) for q in range(n))
    (q0,) = automaton.starts
    start = (f0[q0], f0) if 0 <= q0 < n and f0[q0] is not None else _DEAD

    index = {start: 0}
    queue = deque([start])
    transitions: dict[tuple[int, int], set[int]] = {}
    while queue:
        state = queue.popleft()
        for symbol in range(m):
            target = _DEAD if state == _DEAD else _step(delta, n, state, symbol)
            if target not in index:
                if len(index) >= max_states:
                    raise TooManyStatesError(f"2DFA -> DFA превысил {max_states} состояний")
                index[target] = len(index)
                queue.append(target)
            transitions[(index[state], symbol)] = {index[target]}

    finals = {i for state, i in index.items() if state != _DEAD and _accepts(delta, automaton, state)}
    return Automaton(n=len(index), m=m, starts={0}, finals=finals, transitions=transitions)


def _move_right(delta: dict, q: int, symbol: int) -> int | None:
    move = delta.get((q, symbol))
    return move[0] if move is not None and move[1] == RIGHT else None


def _step(delta: dict, n: int, state: tuple[int, Behavior], symbol: int):
    """(q̂, f) --a--> (f'(q̂), f'): f'(q1) — итерация q1 -a-> налево -> f -> снова на a -> …,
    пока головка не уйдёт с a направо (рис. 9(ii) лекции). Повтор состояния на a — цикл."""
    q_hat, f = state
    new_f: Behavior = tuple(_exit_right(delta, f, q1, symbol) for q1 in range(n))
    exit_state = new_f[q_hat] if 0 <= q_hat < n else None
    return (exit_state, new_f) if exit_state is not None else _DEAD


def _exit_right(delta: dict, f: Behavior, q1: int, symbol: int) -> int | None:
    current, seen = q1, set()
    while current not in seen:
        seen.add(current)
        move = delta.get((current, symbol))
        if move is None:
            return None
        target, direction = move
        if direction == RIGHT:
            return target
        current = f[target] if 0 <= target < len(f) else None  # ушли налево в прочитанную часть
        if current is None:
            return None
    return None  # зациклился, возвращаясь на a в одних и тех же состояниях


def _accepts(delta: dict, automaton: TwoWayAutomaton, state: tuple[int, Behavior]) -> bool:
    """F' = {(q̂, f) | (f∘δ⊣)^k(q̂) ∈ F для некоторого k ≥ 0}: на ⊣ в q̂, затем налево с ⊣,
    возврат на ⊣ через f, и так далее — пока не придём в принимающее, не застрянем или не зациклимся."""
    q_hat, f = state
    current, seen = q_hat, set()
    while current is not None and current not in seen:
        if current in automaton.finals:
            return True
        seen.add(current)
        move = delta.get((current, automaton.right_marker))
        if move is None or move[1] == RIGHT:
            return False
        current = f[move[0]] if 0 <= move[0] < len(f) else None
    return False
