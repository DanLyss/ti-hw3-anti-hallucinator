from dataclasses import dataclass, field

LEFT, RIGHT = -1, 1


@dataclass
class TwoWayAutomaton:
    """2DFA/2NFA по определению 1 из лекции 4 (Рабин и Скотт): лента ⊢ a1 … aℓ ⊣.

    Символы алфавита — индексы 0..m-1, метки начала и конца закодированы как два
    дополнительных индекса: ⊢ = m, ⊣ = m+1 (в формате из листка отдельного способа записать
    переход по меткам нет — это наше соглашение, оно же объясняется модели в промпте)."""

    n: int
    m: int
    starts: set[int]
    finals: set[int]
    # (состояние, символ) -> {(состояние, направление)}, направление ∈ {-1, +1}
    transitions: dict[tuple[int, int], set[tuple[int, int]]] = field(default_factory=dict)

    @property
    def left_marker(self) -> int:
        return self.m

    @property
    def right_marker(self) -> int:
        return self.m + 1
