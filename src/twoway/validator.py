from src.twoway.model import LEFT, RIGHT, TwoWayAutomaton


def validate_two_way(automaton: TwoWayAutomaton, expected_alphabet_size: int | None = None) -> tuple[bool, list[str]]:
    """Проверка формата 2DFA (3 балла): всё, что и для обычного автомата в домашке 3
    (диапазоны, n и m посчитаны правильно), плюс направление строго ±1 и никаких переходов
    за пределы ленты — налево с ⊢ или направо с ⊣."""
    violations: list[str] = []
    n, m = automaton.n, automaton.m

    if n <= 0:
        violations.append(f"число состояний n должно быть положительным, получено {n}")
    if m <= 0:
        violations.append(f"размер алфавита m должен быть положительным, получено {m}")
    if expected_alphabet_size is not None and m != expected_alphabet_size:
        violations.append(f"размер алфавита m={m} не совпадает с алфавитом задачи ({expected_alphabet_size} символов)")
    if n <= 0:
        return False, violations

    for label, states in (("стартовое", automaton.starts), ("финальное", automaton.finals)):
        violations += [f"{label} состояние {q} вне диапазона [0, {n})" for q in sorted(states) if not 0 <= q < n]

    mentioned = automaton.starts | automaton.finals
    for (state, symbol), targets in sorted(automaton.transitions.items()):
        mentioned.add(state)
        if not 0 <= state < n:
            violations.append(f"переход из несуществующего состояния {state} (n={n})")
        if m > 0 and not 0 <= symbol < m + 2:
            violations.append(f"переход по несуществующему символу {symbol} (символы 0..{m - 1}, ⊢={m}, ⊣={m + 1})")
        for target, direction in sorted(targets):
            mentioned.add(target)
            if not 0 <= target < n:
                violations.append(f"переход в несуществующее состояние {target} (n={n})")
            if direction not in (LEFT, RIGHT):
                violations.append(f"направление должно быть -1 или 1, получено {direction}")
            elif symbol == m and direction == LEFT:
                violations.append(f"переход налево с метки начала ⊢ (из состояния {state}) — за пределы ленты")
            elif symbol == m + 1 and direction == RIGHT:
                violations.append(f"переход направо с метки конца ⊣ (из состояния {state}) — за пределы ленты")

    unmentioned = sorted(set(range(n)) - mentioned)
    if unmentioned:
        shown = ", ".join(map(str, unmentioned[:5])) + (", ..." if len(unmentioned) > 5 else "")
        violations.append(f"заявлено n={n}, но {len(unmentioned)} состояний нигде не упоминаются: {shown}")

    return len(violations) == 0, violations


def is_deterministic_two_way(automaton: TwoWayAutomaton) -> bool:
    return len(automaton.starts) == 1 and all(len(t) <= 1 for t in automaton.transitions.values())


def is_really_2dfa(automaton: TwoWayAutomaton) -> bool:
    """«Действительно 2DFA» из листка: детерминизм + хотя бы одно движение налево
    (иначе это просто односторонний DFA, записанный в формате 2DFA)."""
    has_left_move = any(d == LEFT for targets in automaton.transitions.values() for _, d in targets)
    return is_deterministic_two_way(automaton) and has_left_move
