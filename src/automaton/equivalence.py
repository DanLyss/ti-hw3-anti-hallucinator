from src.automaton.determinize import determinize
from src.automaton.minimize import minimize
from src.automaton.model import Automaton


def are_equivalent(first: Automaton, second: Automaton) -> bool:
    """Распознают ли два автомата (NFA или DFA) один и тот же язык.

    Минимальный DFA языка единственен с точностью до переименования состояний, поэтому
    автоматы эквивалентны тогда и только тогда, когда совпадают их минимальные DFA. minimize()
    нумерует состояния BFS-ом от старта с символами по возрастанию — у изоморфных минимальных
    DFA эта нумерация одинакова, и "с точностью до переименования" сводится к обычному ==.
    Автоматы над алфавитами разного размера распознают языки над разными алфавитами —
    неэквивалентны сразу."""
    if first.m != second.m:
        return False
    return minimize(determinize(first)) == minimize(determinize(second))
