from src.automaton.model import Automaton


def simulate(automaton: Automaton, word: list[int]) -> bool:
    """Принимает ли автомат данное слово (список индексов символов). Обход NFA без ε-переходов:
    на каждом шаге держим множество активных состояний, слово принято, если после последнего
    символа хотя бы одно активное состояние — финальное."""
    active = set(automaton.starts)
    for symbol in word:
        if not active:
            return False
        active = {
            target
            for state in active
            for target in automaton.transitions.get((state, symbol), set())
        }
    return bool(active & automaton.finals)


def check_correctness(automaton: Automaton, samples: list[tuple[list[int], bool]]) -> bool:
    """True, если симуляция автомата совпадает с ожидаемым вердиктом на каждом примере."""
    return all(simulate(automaton, word) == expected for word, expected in samples)
