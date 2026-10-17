import json
from itertools import product
from pathlib import Path

import pytest

from src.automaton.minimize import minimize
from src.automaton.parser import ParseError
from src.automaton.simulator import simulate
from src.llm_clients.base import LLMClient
from src.twoway.evaluator import evaluate_all_2dfa
from src.twoway.model import TwoWayAutomaton
from src.twoway.parser import parse_two_way
from src.twoway.prompt_builder import _FEW_SHOT_EXAMPLE, build_prompt_2dfa
from src.twoway.report import render_report_2dfa
from src.twoway.runner import run_testcase
from src.twoway.simulator import simulate_two_way
from src.twoway.testcases import TESTCASES_2DFA, ground_truth_min_dfa
from src.twoway.to_dfa import TooManyStatesError, two_way_to_dfa
from src.twoway.validator import is_really_2dfa, validate_two_way

FIXTURES = Path(__file__).parent / "fixtures"
A, B, LM, RM = 0, 1, 2, 3  # алфавит {a, b}: ⊢ = m = 2, ⊣ = m+1 = 3


def _lecture_example() -> TwoWayAutomaton:
    # Пример 2 лекции 4 при n = 3: (a|b)*a(a|b)^2 — едет к ⊣, разворачивается, отсчитывает 3 символа.
    return parse_two_way((FIXTURES / "2dfa_lecture_example2.txt").read_text())


def _words(max_length: int):
    for length in range(max_length + 1):
        yield from (list(w) for w in product([A, B], repeat=length))


# --- парсер и формат ---

def test_parser_reads_four_number_transitions():
    automaton = _lecture_example()
    assert (automaton.n, automaton.m, automaton.starts, automaton.finals) == (5, 2, {0}, {4})
    assert automaton.transitions[(0, RM)] == {(1, -1)}


def test_parser_rejects_three_number_transition():
    with pytest.raises(ParseError, match="4 чисел"):
        parse_two_way("2\n2\n0\n1\n0 0 1\n")


def test_lecture_example_is_valid_and_really_2dfa():
    automaton = _lecture_example()
    assert validate_two_way(automaton, expected_alphabet_size=2) == (True, [])
    assert is_really_2dfa(automaton)


@pytest.mark.parametrize(
    "extra, message",
    [
        ({(0, 0): {(1, 0)}}, "направление должно быть -1 или 1"),
        ({(1, LM): {(0, -1)}}, "налево с метки начала"),
        ({(1, RM): {(0, 1)}}, "направо с метки конца"),
        ({(0, 7): {(0, 1)}}, "несуществующему символу"),
        ({(9, 0): {(0, 1)}}, "из несуществующего состояния"),
    ],
)
def test_validator_catches_broken_transitions(extra, message):
    automaton = TwoWayAutomaton(n=2, m=2, starts={0}, finals={1}, transitions={(0, LM): {(1, 1)}, **extra})
    is_valid, violations = validate_two_way(automaton)
    assert not is_valid
    assert any(message in v for v in violations)


def test_validator_checks_n_and_m():
    automaton = TwoWayAutomaton(n=4, m=2, starts={0}, finals={1}, transitions={(0, LM): {(1, 1)}})
    is_valid, violations = validate_two_way(automaton, expected_alphabet_size=3)
    assert not is_valid
    assert any("не совпадает с алфавитом задачи" in v for v in violations)
    assert any("заявлено n=4" in v for v in violations)


def test_one_way_and_nondeterministic_are_not_really_2dfa():
    one_way = TwoWayAutomaton(n=1, m=2, starts={0}, finals={0},
                              transitions={(0, LM): {(0, 1)}, (0, A): {(0, 1)}, (0, B): {(0, 1)}})
    nondeterministic = _lecture_example()
    nondeterministic.transitions[(0, A)].add((1, -1))
    assert not is_really_2dfa(one_way)
    assert not is_really_2dfa(nondeterministic)


# --- симулятор ---

def test_simulator_on_lecture_example_matches_language():
    automaton = _lecture_example()
    assert simulate_two_way(automaton, [A, B, A, A, B])  # abaab из рис. 7: принимается
    for word in _words(9):
        assert simulate_two_way(automaton, word) == (len(word) >= 3 and word[-3] == A)


def test_simulator_rejects_on_infinite_loop():
    # Бесконечно ходит туда-обратно между ⊢ и первым символом.
    looping = TwoWayAutomaton(n=1, m=2, starts={0}, finals={0},
                              transitions={(0, LM): {(0, 1)}, (0, A): {(0, -1)}})
    assert not simulate_two_way(looping, [A])


def test_simulator_empty_word_and_falling_off_tape():
    accepts_empty = TwoWayAutomaton(n=2, m=2, starts={0}, finals={1}, transitions={(0, LM): {(1, 1)}})
    assert simulate_two_way(accepts_empty, [])  # ⊢ -> сразу на ⊣ в принимающем
    assert not simulate_two_way(accepts_empty, [A])  # перехода по a нет


def test_prompt_example_is_correct():
    # Пример из промпта ("последний символ равен 1") — сам по себе правильный 2DFA.
    example = parse_two_way(_FEW_SHOT_EXAMPLE.split(":\n", 1)[1])
    for word in _words(8):
        assert simulate_two_way(example, word) == (len(word) > 0 and word[-1] == B)


# --- 2DFA -> DFA ---

def test_lecture_example_gives_9_state_dfa_as_in_figure_10():
    # Рис. 10 лекции: 9 состояний (q̂, f), мёртвого нет — у всякой строки есть продолжение в языке.
    dfa = two_way_to_dfa(_lecture_example())
    assert dfa.n == 9
    assert minimize(dfa).n == 8  # минимальный DFA для "третий с конца — a"


def test_conversion_preserves_language():
    automaton = _lecture_example()
    dfa = two_way_to_dfa(automaton)
    for word in _words(10):
        assert simulate(dfa, word) == simulate_two_way(automaton, word)


def test_one_way_2dfa_converts_to_the_same_dfa():
    # Только движения направо: DFA "чётное число a" на 2 состояниях + проход по ⊢.
    one_way = TwoWayAutomaton(n=2, m=2, starts={0}, finals={0}, transitions={
        (0, LM): {(0, 1)}, (0, A): {(1, 1)}, (0, B): {(0, 1)}, (1, A): {(0, 1)}, (1, B): {(1, 1)},
    })
    minimal = minimize(two_way_to_dfa(one_way))
    assert minimal.n == 2
    for word in _words(8):
        assert simulate(minimal, word) == (word.count(A) % 2 == 0)


def test_dead_state_when_2dfa_never_leaves_prefix():
    # По b уходит налево и зацикливается — после b 2DFA никогда не выйдет направо.
    automaton = TwoWayAutomaton(n=1, m=2, starts={0}, finals={0}, transitions={
        (0, LM): {(0, 1)}, (0, A): {(0, 1)}, (0, B): {(0, -1)},
    })
    dfa = two_way_to_dfa(automaton)
    for word in _words(6):
        assert simulate(dfa, word) == (B not in word) == simulate_two_way(automaton, word)


def test_conversion_rejects_nondeterministic_and_limits_size():
    nondeterministic = _lecture_example()
    nondeterministic.starts = {0, 1}
    with pytest.raises(ValueError):
        two_way_to_dfa(nondeterministic)
    with pytest.raises(TooManyStatesError):
        two_way_to_dfa(_lecture_example(), max_states=3)


# --- тесткейсы и ground truth ---

@pytest.mark.parametrize("testcase_id, expected_states", [("2dfa_basic", 16), ("2dfa_grob", 8)])
def test_ground_truth_min_dfa_matches_predicate(testcase_id, expected_states):
    testcase = TESTCASES_2DFA[testcase_id]
    dfa = ground_truth_min_dfa(testcase_id)
    assert dfa.n == expected_states
    assert minimize(dfa) == dfa
    for length in range(17):
        for word in map("".join, product("01", repeat=length)):
            assert simulate(dfa, testcase.encode(word)) == testcase.ground_truth(word), word


@pytest.mark.parametrize(
    "word, expected",
    [("0" * 14, True), ("10" + "1" * 12, True), ("11" + "0" * 12, False), ("0" * 13, False), ("0" * 15, False)],
)
def test_basic_ground_truth(word, expected):
    assert TESTCASES_2DFA["2dfa_basic"].ground_truth(word) == expected


@pytest.mark.parametrize(
    "word, expected",
    [("", True), ("0", True), ("1", True), ("01", True), ("011", False), ("10", True), ("110", False), ("101", False), ("100", True)],
)
def test_grob_ground_truth(word, expected):
    # "011": ww = 011011 и "101": ww = 101101 — 110 на стыке половин; "10": ww = 1010, "100": 100100 — нет.
    assert TESTCASES_2DFA["2dfa_grob"].ground_truth(word) == expected


# --- промпт, раннер, оценка, отчёт ---

def test_prompt_explains_2dfa_markers_and_description():
    prompt = build_prompt_2dfa("описание", ("0", "1"))
    assert "описание" in prompt
    assert "2 -> '⊢'" in prompt and "3 -> '⊣'" in prompt
    assert "направление" in prompt


class _FakeClient(LLMClient):
    def __init__(self, response: str):
        self.response, self.calls = response, 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return self.response


def test_runner_writes_runs_and_skips_existing(tmp_path):
    client = _FakeClient("ответ")
    run_testcase("fake", client, "2dfa_grob", runs=3, out_root=tmp_path, pacing_seconds=0)
    run_testcase("fake", client, "2dfa_grob", runs=3, out_root=tmp_path, pacing_seconds=0)
    assert sorted(p.name for p in (tmp_path / "fake" / "2dfa_grob").iterdir()) == ["run_000.txt", "run_001.txt", "run_002.txt"]
    assert client.calls == 3


class _FlakyClient(LLMClient):
    """Первые `failures` вызовов падают, как при пропавшем интернете."""

    def __init__(self, failures: int):
        self.failures, self.calls = failures, 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("нет сети")
        return "ответ"


def test_runner_survives_network_outage(tmp_path):
    client = _FlakyClient(failures=3)
    run_testcase("fake", client, "2dfa_basic", runs=2, out_root=tmp_path, pacing_seconds=0, outage_pause_seconds=0)
    assert sorted(p.name for p in (tmp_path / "fake" / "2dfa_basic").iterdir()) == ["run_000.txt", "run_001.txt"]
    assert client.calls == 5  # 3 падения + 2 успешных запроса, ничего не потеряно


def test_evaluator_and_report(tmp_path):
    raw = tmp_path / "raw"
    out = raw / "modelA" / "2dfa_grob"
    out.mkdir(parents=True)
    # Правильный ответ: тот же DFA, что ground truth, записанный как одностороннний 2DFA (+ проход по ⊢).
    gt = ground_truth_min_dfa("2dfa_grob")
    lines = [str(gt.n), "2", "0", " ".join(map(str, sorted(gt.finals)))]
    lines += [f"{q} 2 {q} 1" for q in [0]] + [f"{q} {c} {next(iter(t))} 1" for (q, c), t in sorted(gt.transitions.items())]
    (out / "run_000.txt").write_text("\n".join(lines), encoding="utf-8")
    (out / "run_001.txt").write_text("не автомат", encoding="utf-8")
    (out / "run_002.txt").write_text((FIXTURES / "2dfa_lecture_example2.txt").read_text(), encoding="utf-8")

    results_path = tmp_path / "runs.jsonl"
    by_run = {r.run_id: r for r in evaluate_all_2dfa(raw, results_path)}
    assert by_run["000"].is_correct is True and by_run["000"].is_really_2dfa is False  # одностороннний
    assert by_run["001"].is_format_valid is False and by_run["001"].is_correct is None
    assert by_run["002"].is_correct is False and by_run["002"].is_really_2dfa is True
    assert by_run["002"].dfa_state_count == 9

    report_path = tmp_path / "report.md"
    render_report_2dfa(results_path, report_path)
    report = report_path.read_text(encoding="utf-8")
    assert "Действительно 2DFA, % (modelA)" in report
    assert "| total |" in report
    assert len(json.loads(results_path.read_text(encoding="utf-8").splitlines()[0])) > 0
