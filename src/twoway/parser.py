from src.automaton.parser import ParseError, _parse_int, _parse_int_list, _strip_code_fence
from src.twoway.model import TwoWayAutomaton


def parse_two_way(text: str) -> TwoWayAutomaton:
    """Текст -> TwoWayAutomaton. Формат из листка домашки 5: n / m / старты / финалы /
    переходы "откуда символ куда направление" (4 числа на строку). Синтаксические ошибки
    собираются в один ParseError, диапазоны и направления проверяет validate_two_way()."""
    text = _strip_code_fence(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    violations: list[str] = []

    if len(lines) < 4:
        raise ParseError([f"ожидается минимум 4 строки заголовка (n, m, старты, финалы), получено {len(lines)}"])

    n = _parse_int(lines[0], violations, "строка 1 (n)")
    m = _parse_int(lines[1], violations, "строка 2 (m)")
    starts = _parse_int_list(lines[2], violations, "строка 3 (стартовые состояния)")
    finals = _parse_int_list(lines[3], violations, "строка 4 (финальные состояния)")

    transitions: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for i, line in enumerate(lines[4:], start=5):
        tokens = line.split()
        if len(tokens) != 4:
            violations.append(
                f"строка {i}: переход 2DFA должен состоять из 4 чисел (откуда символ куда направление), "
                f"получено {len(tokens)}: {line!r}"
            )
            continue
        values = [_parse_int(token, violations, f"строка {i}") for token in tokens]
        if None in values:
            continue
        from_state, symbol, to_state, direction = values
        transitions.setdefault((from_state, symbol), set()).add((to_state, direction))

    if violations:
        raise ParseError(violations)
    return TwoWayAutomaton(n=n, m=m, starts=set(starts), finals=set(finals), transitions=transitions)
