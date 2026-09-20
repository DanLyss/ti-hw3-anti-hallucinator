from src.automaton.model import Automaton


class ParseError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


def parse(text: str) -> Automaton:
    """Разбирает текстовый формат автомата. Реализация — Этап 1 (PLAN.md)."""
    raise NotImplementedError
