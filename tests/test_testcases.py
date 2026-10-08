import pytest

from src.testcases import TESTCASES


@pytest.mark.parametrize("testcase_id", list(TESTCASES.keys()))
def test_sample_strings_are_labeled_consistently_with_ground_truth(testcase_id):
    testcase = TESTCASES[testcase_id]
    samples = testcase.sample_strings()
    assert samples, f"{testcase_id}: sample_strings() ничего не вернул"
    for word, label in samples:
        assert testcase.ground_truth(word) == label
        assert all(ch in testcase.alphabet for ch in word)


@pytest.mark.parametrize("testcase_id", list(TESTCASES.keys()))
def test_sample_strings_contain_both_labels(testcase_id):
    testcase = TESTCASES[testcase_id]
    labels = {label for _, label in testcase.sample_strings()}
    assert labels == {True, False}, f"{testcase_id}: нет примеров обоих классов: {labels}"


@pytest.mark.parametrize("testcase_id", list(TESTCASES.keys()))
def test_sample_strings_are_balanced_and_large_enough(testcase_id):
    samples = TESTCASES[testcase_id].sample_strings()
    positives = [w for w, label in samples if label]
    negatives = [w for w, label in samples if not label]
    assert len(positives) == len(negatives) >= 15
    assert len(set(positives)) == len(positives) and len(set(negatives)) == len(negatives)


def test_sample_strings_fail_loudly_when_candidates_are_not_enough():
    with pytest.raises(ValueError, match="basic"):
        TESTCASES["basic"].sample_strings(per_label=1000)


@pytest.mark.parametrize(
    "word,expected",
    [("", False), ("1", True), ("010", True), ("1010", False), ("0", False)],
)
def test_basic_ground_truth(word, expected):
    assert TESTCASES["basic"].ground_truth(word) == expected


@pytest.mark.parametrize(
    "word,expected",
    [("", False), ("111", False), ("1000", True), ("0001", False), ("10001", False)],
)
def test_fourth_symbol_ground_truth(word, expected):
    assert TESTCASES["4th-symbol"].ground_truth(word) == expected


@pytest.mark.parametrize(
    "word,expected",
    [
        ("SPB1234", True),
        ("SPB0234", False),  # SPB не может начинаться с 0
        ("MSC0234", True),  # не SPB — 0 разрешён
        ("SPB123", False),  # длина 6, а не 7
        ("XYZ1234", False),  # буквы вне алфавита
    ],
)
def test_employer_ground_truth(word, expected):
    assert TESTCASES["employer"].ground_truth(word) == expected


@pytest.mark.parametrize(
    "word,expected",
    [
        ("101", True),  # длина 3, w[-3]='1', ровно один 0
        ("110", True),  # длина 3, w[-3]='1', ровно один 0
        ("100", False),  # w[-3]='1', но два 0
        ("010", False),  # w[-3]='0'
        ("1000", False),  # w[-3]='0' (длина 4, третий с конца — индекс 1)
    ],
)
def test_intersection_ground_truth(word, expected):
    assert TESTCASES["intersection"].ground_truth(word) == expected


@pytest.mark.parametrize(
    "word,expected",
    [("", True), ("0", True), ("11", True), ("1", False), ("10", False), ("110", True)],
)
def test_personal_ground_truth(word, expected):
    assert TESTCASES["personal"].ground_truth(word) == expected
