from dataclasses import dataclass, field


@dataclass
class Automaton:
    n: int
    m: int
    starts: set[int]
    finals: set[int]
    transitions: dict[tuple[int, int], set[int]] = field(default_factory=dict)
