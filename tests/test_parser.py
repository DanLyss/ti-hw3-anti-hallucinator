from pathlib import Path

import pytest

from src.automaton.parser import ParseError, parse

FIXTURES = Path(__file__).parent / "fixtures"
PDF_EXAMPLE = (FIXTURES / "pdf_example.txt").read_text()


def test_parses_pdf_example():
    automaton = parse(PDF_EXAMPLE)
    assert automaton.n == 3
    assert automaton.m == 2
    assert automaton.starts == {0}
    assert automaton.finals == {1}
    assert automaton.transitions == {
        (0, 0): {1, 2},
        (0, 1): {2},
        (1, 0): {2},
        (2, 1): {2},
        (2, 0): {0},
    }


def test_strips_markdown_code_fence():
    wrapped = f"Вот автомат:\n```\n{PDF_EXAMPLE}```\nНадеюсь, помог!"
    automaton = parse(wrapped)
    assert automaton.n == 3
    assert automaton.transitions[(0, 0)] == {1, 2}


def test_ignores_blank_lines_between_sections():
    spaced = PDF_EXAMPLE.replace("\n", "\n\n")
    automaton = parse(spaced)
    assert automaton.n == 3
    assert automaton.transitions[(2, 0)] == {0}


@pytest.mark.parametrize(
    "broken_text,expected_fragment",
    [
        ("3\n2\n0\n", "минимум 4 строки"),
        ("abc\n2\n0\n1\n0 0 1\n", "строка 1 (n)"),
        ("3\n2\n0\n1\n0 0\n", "должен состоять из 3 чисел"),
        ("3\n2\n0\n1\nA 0 1\n", "состояние-источник"),
        ("3\n2\n0 x\n1\n0 0 1\n", "стартовые состояния"),
        ("3\n2\n0\n1\n0 x 1\n", "символ"),
    ],
)
def test_broken_inputs_raise_parse_error(broken_text, expected_fragment):
    with pytest.raises(ParseError) as exc_info:
        parse(broken_text)
    assert any(expected_fragment in v for v in exc_info.value.violations)
