from src.automaton.model import Automaton


def _check_states(states: set[int], n: int, label: str, violations: list[str]) -> None:
    for state in states:
        if not (0 <= state < n):
            violations.append(f"{label}: состояние {state} вне диапазона [0, {n})")


def validate(automaton: Automaton, expected_alphabet_size: int | None = None) -> tuple[bool, list[str]]:
    """Семантические проверки корректности формата (не путать с парсингом текста):
    диапазоны индексов состояний/символов, отсутствие переходов из/в несуществующие состояния,
    правильно ли посчитаны n и m. Заявленное n сверяем с реально упомянутыми состояниями
    (завышенное n — "фантомные" состояния, которых нет ни в стартах, ни в финалах, ни в
    переходах; заниженное ловится проверкой диапазонов), m — с размером алфавита тесткейса,
    если он передан.
    """
    violations: list[str] = []

    if automaton.n <= 0:
        violations.append(f"число состояний n должно быть положительным, получено {automaton.n}")
    if automaton.m <= 0:
        violations.append(f"размер алфавита m должен быть положительным, получено {automaton.m}")
    if expected_alphabet_size is not None and automaton.m != expected_alphabet_size:
        violations.append(
            f"размер алфавита m={automaton.m} не совпадает с алфавитом задачи ({expected_alphabet_size} символов)"
        )

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

        _check_all_states_mentioned(automaton, violations)

    return (len(violations) == 0, violations)


def _check_all_states_mentioned(automaton: Automaton, violations: list[str]) -> None:
    mentioned = automaton.starts | automaton.finals
    for (state, _), targets in automaton.transitions.items():
        mentioned |= {state} | targets
    unmentioned = sorted(set(range(automaton.n)) - mentioned)
    if unmentioned:
        shown = ", ".join(map(str, unmentioned[:5])) + (", ..." if len(unmentioned) > 5 else "")
        violations.append(
            f"заявлено n={automaton.n}, но {len(unmentioned)} состояний нигде не упоминаются "
            f"(ни в стартах, ни в финалах, ни в переходах): {shown}"
        )


def is_deterministic(automaton: Automaton) -> bool:
    """DFA: ровно одно стартовое состояние и не более одного перехода на (состояние, символ).
    Частично заданный DFA (не для каждой пары есть переход) — всё ещё детерминированный."""
    if len(automaton.starts) != 1:
        return False
    return all(len(targets) <= 1 for targets in automaton.transitions.values())
