from pathlib import Path

from src.automaton.model import Automaton


def to_text(automaton: Automaton) -> str:
    """Automaton -> текст в формате из домашки (тот же, что читает parser.parse):
    n / m / старты / финалы / переходы "откуда символ куда", по одному на строку."""
    lines = [
        str(automaton.n),
        str(automaton.m),
        " ".join(map(str, sorted(automaton.starts))),
        " ".join(map(str, sorted(automaton.finals))),
    ]
    for (state, symbol), targets in sorted(automaton.transitions.items()):
        lines += [f"{state} {symbol} {target}" for target in sorted(targets)]
    return "\n".join(lines) + "\n"


def write_automaton(automaton: Automaton, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_text(automaton), encoding="utf-8")
