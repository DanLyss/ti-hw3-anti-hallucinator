import random
from dataclasses import dataclass
from itertools import product
from typing import Callable

_BINARY_ALPHABET: tuple[str, ...] = ("0", "1")
_SHUFFLE_SEED = 42
SAMPLES_PER_LABEL = 20


@dataclass
class TestCase:
    id: str
    description: str
    alphabet: tuple[str, ...]
    ground_truth: Callable[[str], bool]
    candidate_words: Callable[[], list[str]]

    def encode(self, word: str) -> list[int]:
        index = {ch: i for i, ch in enumerate(self.alphabet)}
        return [index[ch] for ch in word]

    def sample_strings(self, per_label: int = SAMPLES_PER_LABEL) -> list[tuple[str, bool]]:
        """Позитивные/негативные примеры для симулятора — строго поровну, по per_label
        каждого класса. Кандидаты берутся из candidate_words() и размечаются самим
        ground_truth — так разметка не может разойтись с определением языка. Если среди
        кандидатов не набирается per_label примеров какого-то класса — это ошибка в
        candidate_words тесткейса, а не повод молча вернуть несбалансированную выборку."""
        candidates = list(dict.fromkeys(self.candidate_words()))  # без дублей, порядок сохраняется
        random.Random(_SHUFFLE_SEED).shuffle(candidates)

        positives: list[tuple[str, bool]] = []
        negatives: list[tuple[str, bool]] = []
        for word in candidates:
            label = self.ground_truth(word)
            bucket = positives if label else negatives
            if len(bucket) < per_label:
                bucket.append((word, label))
            if len(positives) >= per_label and len(negatives) >= per_label:
                break
        if len(positives) < per_label or len(negatives) < per_label:
            raise ValueError(
                f"{self.id}: среди кандидатов {len(positives)} позитивов и {len(negatives)} "
                f"негативов, нужно по {per_label}"
            )
        return positives + negatives


def _brute_force_candidates(alphabet: tuple[str, ...], max_length: int) -> Callable[[], list[str]]:
    def _gen() -> list[str]:
        return [
            "".join(combo)
            for length in range(max_length + 1)
            for combo in product(alphabet, repeat=length)
        ]

    return _gen


def _basic_candidates() -> list[str]:
    # Язык basic очень разреженный: без 00/11 слово чередующееся, и подходит ровно одно
    # чередующееся слово на каждую нечётную длину (1, 010, 10101, 0101010, ...). Перебором
    # до длины 12 позитивов набирается всего 6, поэтому добавляем все чередующиеся слова
    # до длины 40 — среди них и позитивы, и "трудные" негативы (без 00/11, но с неверной
    # чётностью).
    alternating = [
        "".join("01"[(start + i) % 2] for i in range(length))
        for length in range(1, 41)
        for start in (0, 1)
    ]
    return _brute_force_candidates(_BINARY_ALPHABET, max_length=10)() + alternating


def _employer_candidates() -> list[str]:
    # Позитивы: разные регионы (в т.ч. SPB с ненулевой первой цифрой и не-SPB с нулём).
    regions = ["MSC", "CAB", "AAA", "BPS", "SPA", "PBS", "SSS", "MMM"]
    digit_groups = ["0123", "1234", "5555", "0000", "5000", "3021"]
    positives = [region + digits for region in regions for digits in digit_groups]
    positives += ["SPB" + digits for digits in ["1234", "5555", "5000", "2010", "1000", "3333"]]
    # Негативы — по несколько штук на каждый тип ошибки, чтобы выборка не состояла из
    # одного типа (раньше были только "неверная длина" и "SPB с нулём").
    negatives = [
        "SPB0123", "SPB0000", "SPB0555", "SPB0012", "SPB0321",  # SPB + ведущий 0
        "", "SPB", "MSC123", "MSC12345", "CAB01234", "AAA1",  # неверная длина
        "1AB1234", "A2C1234", "AB01234", "0001234", "S5B1234",  # цифра на месте буквы
        "MSCA234", "CAB12B4", "SPB123S", "AAAAAAA", "BPS1S34",  # буква на месте цифры
        "1234ABC", "0123SPB", "55MSC55",  # части перепутаны местами
    ]
    return positives + negatives


def _basic_ground_truth(w: str) -> bool:
    if any(w[i] == w[i + 1] for i in range(len(w) - 1)):
        return False  # подстрока "00" или "11"
    zeros = w.count("0")
    ones = w.count("1")
    return zeros % 2 == 0 and ones % 2 == 1


def _fourth_symbol_ground_truth(w: str) -> bool:
    return len(w) >= 4 and w[-4] == "1"


def _employer_ground_truth(w: str) -> bool:
    letters = set("AMCSPB")
    digits = set("012345")
    if len(w) != 7:
        return False
    region, digit_part = w[:3], w[3:]
    if not all(c in letters for c in region):
        return False
    if not all(c in digits for c in digit_part):
        return False
    if region == "SPB" and digit_part[0] == "0":
        return False
    return True


def _intersection_ground_truth(w: str) -> bool:
    # L = (A)^R \cap B, A = {третий символ с начала = 1}, B = {ровно один 0}.
    # (A)^R = {w : третий символ С КОНЦА (w[-3]) = 1} — реверс сдвигает позицию с начала на позицию с конца.
    if len(w) < 3:
        return False
    if w[-3] != "1":
        return False
    return w.count("0") == 1


def _personal_ground_truth(w: str) -> bool:
    # Свой пример: двоичная запись числа (с ведущими нулями или без — не важно) делится на 3.
    value = int(w, 2) if w else 0
    return value % 3 == 0


TESTCASES: dict[str, TestCase] = {
    "basic": TestCase(
        id="basic",
        description=(
            "число ноликов чётно, число единиц нечётно, нет подстрок 00 и нет подстрок 11, "
            "алфавит {0 , 1}"
        ),
        alphabet=_BINARY_ALPHABET,
        ground_truth=_basic_ground_truth,
        candidate_words=_basic_candidates,
    ),
    "4th-symbol": TestCase(
        id="4th-symbol",
        description="четвёртый символ с конца равен 1, алфавит {0 , 1}",
        alphabet=_BINARY_ALPHABET,
        ground_truth=_fourth_symbol_ground_truth,
        candidate_words=_brute_force_candidates(_BINARY_ALPHABET, max_length=9),
    ),
    "employer": TestCase(
        id="employer",
        description=(
            "ID сотрудника: начинается с 3 букв региона,\n"
            "потом 4 цифры, причем если регион SPB,\n"
            "то цифры не могут начинаться с нуля,\n"
            "алфавит для простоты возьмем такой: {A, M, C, S, P, B, 0, 1, 2, 3, 4, 5}"
        ),
        alphabet=("A", "M", "C", "S", "P", "B", "0", "1", "2", "3", "4", "5"),
        ground_truth=_employer_ground_truth,
        candidate_words=_employer_candidates,
    ),
    "intersection": TestCase(
        id="intersection",
        description=(
            r"L = (A)^R \cap B, "
            r"где A = \{w \in \{0, 1\}^*, третий символ с начала равен 1\}, "
            r"B = \{w \in \{0, 1\}^*, w содержит ровно один 0\}"
        ),
        alphabet=_BINARY_ALPHABET,
        ground_truth=_intersection_ground_truth,
        candidate_words=_brute_force_candidates(_BINARY_ALPHABET, max_length=9),
    ),
    "personal": TestCase(
        id="personal",
        description=(
            "Число, записанное в двоичной системе счисления (ведущие нули допускаются, "
            "пустая строка означает 0), делится на 3, алфавит {0, 1}"
        ),
        alphabet=_BINARY_ALPHABET,
        ground_truth=_personal_ground_truth,
        candidate_words=_brute_force_candidates(_BINARY_ALPHABET, max_length=10),
    ),
}
