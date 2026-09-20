from collections import deque

from src.automaton.model import Automaton


class TooManyStatesError(Exception):
    """NFA->DFA превысил разумный лимит состояний — скорее всего, вырожденный/
    галлюцинированный вход (в реальных данных уже встречался автомат на 280+ строк
    переходов), а не осмысленная задача на построение подмножеств."""


def determinize(automaton: Automaton, max_states: int = 20_000) -> Automaton:
    """NFA -> DFA построением подмножеств. Идём лениво от стартового множества (BFS),
    открывая только реально достижимые подмножества — никогда не перебираем все 2^n
    заранее. Если для (подмножество, символ) объединение переходов пусто, переход просто
    не добавляется (частичный DFA) — специально не заводим фиктивное sink-состояние,
    чтобы не раздувать число состояний искусственно (решение задокументировано в
    ARCHITECTURE.md §5)."""
    start_subset = frozenset(automaton.starts)
    subset_to_index: dict[frozenset[int], int] = {start_subset: 0}
    queue: deque[frozenset[int]] = deque([start_subset])
    transitions: dict[tuple[int, int], set[int]] = {}

    while queue:
        subset = queue.popleft()
        state_index = subset_to_index[subset]
        for symbol in range(automaton.m):
            target = frozenset(
                to_state
                for state in subset
                for to_state in automaton.transitions.get((state, symbol), set())
            )
            if not target:
                continue
            if target not in subset_to_index:
                if len(subset_to_index) >= max_states:
                    raise TooManyStatesError(
                        f"NFA->DFA превысил {max_states} состояний, остановлено"
                    )
                subset_to_index[target] = len(subset_to_index)
                queue.append(target)
            transitions[(state_index, symbol)] = {subset_to_index[target]}

    finals = {
        index for subset, index in subset_to_index.items() if subset & automaton.finals
    }

    return Automaton(
        n=len(subset_to_index),
        m=automaton.m,
        starts={0},
        finals=finals,
        transitions=transitions,
    )
