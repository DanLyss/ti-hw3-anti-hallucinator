import random
from dataclasses import dataclass
from itertools import product
from typing import Callable

Word = str

_BINARY_ALPHABET: tuple[str, ...] = ("0", "1")
_SHUFFLE_SEED = 42


@dataclass
class TestCase:
    id: str
    description: str
    alphabet: tuple[str, ...]
    ground_truth: Callable[[Word], bool]
    candidate_words: Callable[[], list[Word]]

    def encode(self, word: Word) -> list[int]:
        index = {ch: i for i, ch in enumerate(self.alphabet)}
        return [index[ch] for ch in word]

    def sample_strings(self, limit_per_label: int = 10) -> list[tuple[Word, bool]]:
        """Позитивные/негативные примеры для симулятора. Кандидаты берутся из
        candidate_words() и размечаются самим ground_truth — так разметка не может
        разойтись с определением языка. Если позитивов/негативов среди кандидатов
        меньше лимита, возвращается сколько есть (language может быть разреженным,
        как в basic — это нормально, не ошибка)."""
        candidates = list(self.candidate_words())
        random.Random(_SHUFFLE_SEED).shuffle(candidates)

        positives: list[tuple[Word, bool]] = []
        negatives: list[tuple[Word, bool]] = []
        for word in candidates:
            label = self.ground_truth(word)
            bucket = positives if label else negatives
            if len(bucket) < limit_per_label:
                bucket.append((word, label))
            if len(positives) >= limit_per_label and len(negatives) >= limit_per_label:
                break
        return positives + negatives


def _brute_force_candidates(alphabet: tuple[str, ...], max_length: int) -> Callable[[], list[Word]]:
    def _gen() -> list[Word]:
        return [
            "".join(combo)
            for length in range(max_length + 1)
            for combo in product(alphabet, repeat=length)
        ]

    return _gen


def _employer_candidates() -> list[Word]:
    regions = ["SPB", "MSC", "CAB", "AAA", "BPS"]
    digit_groups = ["0123", "1234", "5555", "0000", "5000"]
    words = [region + digits for region in regions for digits in digit_groups]
    words += ["SPB123", "SPB01234", "", "SPB"]  # заведомо неверная длина
    return words


def _basic_ground_truth(w: Word) -> bool:
    if any(w[i] == w[i + 1] for i in range(len(w) - 1)):
        return False  # подстрока "00" или "11"
    zeros = w.count("0")
    ones = w.count("1")
    return zeros % 2 == 0 and ones % 2 == 1


def _fourth_symbol_ground_truth(w: Word) -> bool:
    return len(w) >= 4 and w[-4] == "1"


def _employer_ground_truth(w: Word) -> bool:
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


def _intersection_ground_truth(w: Word) -> bool:
    # L = (A)^R \cap B, A = {третий символ с начала = 1}, B = {ровно один 0}.
    # (A)^R = {w : третий символ С КОНЦА (w[-3]) = 1} — реверс сдвигает позицию с начала на позицию с конца.
    if len(w) < 3:
        return False
    if w[-3] != "1":
        return False
    return w.count("0") == 1


def _personal_ground_truth(w: Word) -> bool:
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
        candidate_words=_brute_force_candidates(_BINARY_ALPHABET, max_length=12),
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
