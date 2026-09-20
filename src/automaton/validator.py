from src.automaton.model import Automaton


def _check_states(states: set[int], n: int, label: str, violations: list[str]) -> None:
    for state in states:
        if not (0 <= state < n):
            violations.append(f"{label}: состояние {state} вне диапазона [0, {n})")


def validate(automaton: Automaton) -> tuple[bool, list[str]]:
    """Семантические проверки корректности формата (не путать с парсингом текста):
    диапазоны индексов состояний/символов, отсутствие переходов из/в несуществующие состояния.
    """
    violations: list[str] = []

    if automaton.n <= 0:
        violations.append(f"число состояний n должно быть положительным, получено {automaton.n}")
    if automaton.m <= 0:
        violations.append(f"размер алфавита m должен быть положительным, получено {automaton.m}")

    if automaton.n > 0:
        _check_states(automaton.starts, automaton.n, "стартовое состояние", violations)
        _check_states(automaton.finals, automaton.n, "финальное состояние", violations)

        for (state, symbol), targets in automaton.transitions.items():
            if not (0 <= state < automaton.n):
                violations.append(f"переход из несуществующего состояния {state} (n={automaton.n})")
            if automaton.m > 0 and not (0 <= symbol < automaton.m):
                violations.append(f"переход по несуществующему символу {symbol} (m={automaton.m})")
            for target in targets:
                if not (0 <= target < automaton.n):
                    violations.append(
                        f"переход в несуществующее состояние {target} (n={automaton.n})"
                    )

    return (len(violations) == 0, violations)
