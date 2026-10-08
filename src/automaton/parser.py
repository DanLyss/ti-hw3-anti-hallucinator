import re

from src.automaton.model import Automaton

# Модели иногда оборачивают ответ в markdown-код-блок — вырезаем содержимое первого такого
# блока, если он есть, иначе парсим текст как есть (решение зафиксировано в ARCHITECTURE.md §5).
_CODE_FENCE_RE = re.compile(r"```(?:[a-zA-Z]*\n)?(.*?)```", re.DOTALL)


class ParseError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


def _strip_code_fence(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1) if match else text


def _parse_int(token: str, violations: list[str], context: str) -> int | None:
    try:
        return int(token)
    except ValueError:
        violations.append(f"{context}: ожидалось целое число, получено {token!r}")
        return None


def _parse_int_list(line: str, violations: list[str], context: str) -> list[int]:
    result = []
    for token in line.split():
        value = _parse_int(token, violations, context)
        if value is not None:
            result.append(value)
    return result


def parse(text: str) -> Automaton:
    """Разбирает текстовый формат автомата (см. TCS_2026_hw3.pdf, стр. 1).

    Формат: n / m / стартовые состояния / финальные состояния / список переходов
    "откуда символ куда" (по одному на строку). Синтаксически некорректные строки
    собираются в единый список нарушений и поднимаются одним ParseError — семантические
    проверки (диапазоны индексов и т.д.) делает отдельно automaton.validator.validate().
    """
    text = _strip_code_fence(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    violations: list[str] = []

    if len(lines) < 4:
        violations.append(
            f"ожидается минимум 4 строки заголовка (n, m, старты, финалы), получено {len(lines)}"
        )
        raise ParseError(violations)

    n = _parse_int(lines[0], violations, "строка 1 (n)")
    m = _parse_int(lines[1], violations, "строка 2 (m)")
    starts = _parse_int_list(lines[2], violations, "строка 3 (стартовые состояния)")
    finals = _parse_int_list(lines[3], violations, "строка 4 (финальные состояния)")

    transitions: dict[tuple[int, int], set[int]] = {}
    for i, line in enumerate(lines[4:], start=5):
        tokens = line.split()
        if len(tokens) != 3:
            violations.append(
                f"строка {i}: переход должен состоять из 3 чисел (откуда символ куда), "
                f"получено {len(tokens)}: {line!r}"
            )
            continue
        from_state = _parse_int(tokens[0], violations, f"строка {i} (состояние-источник)")
        symbol = _parse_int(tokens[1], violations, f"строка {i} (символ)")
        to_state = _parse_int(tokens[2], violations, f"строка {i} (состояние-приёмник)")
        if from_state is None or symbol is None or to_state is None:
            continue
        transitions.setdefault((from_state, symbol), set()).add(to_state)

    if violations:
        raise ParseError(violations)

    return Automaton(n=n, m=m, starts=set(starts), finals=set(finals), transitions=transitions)
