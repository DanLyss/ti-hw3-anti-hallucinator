from src.twoway.model import RIGHT, TwoWayAutomaton
from src.twoway.validator import is_deterministic_two_way


def simulate_two_way(automaton: TwoWayAutomaton, word: list[int]) -> bool:
    """Вычисление 2DFA по определению 1 из лекции: старт (q0, 0) на ⊢, лента ⊢ word ⊣.
    Слово принято, когда головка приходит на ⊣ в принимающем состоянии — так же определено
    множество F' в преобразовании к DFA ((f∘δ⊣)^k(q̂) ∈ F). Неопределённый переход, выход за
    пределы ленты и зацикливание (повтор конфигурации) — отказ."""
    if not is_deterministic_two_way(automaton):
        raise ValueError("simulate_two_way() моделирует только детерминированные 2DFA")
    tape = [automaton.left_marker, *word, automaton.right_marker]
    (state,) = automaton.starts
    position = 0
    seen: set[tuple[int, int]] = set()
    while True:
        if position == len(tape) - 1 and state in automaton.finals:
            return True
        if (state, position) in seen:
            return False  # зациклился
        seen.add((state, position))
        targets = automaton.transitions.get((state, tape[position]))
        if not targets:
            return False
        ((state, direction),) = targets
        position += 1 if direction == RIGHT else -1
        if not 0 <= position < len(tape):
            return False
