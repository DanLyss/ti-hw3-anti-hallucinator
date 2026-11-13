import json
import re
from itertools import product

import pytest

from src.automaton.equivalence import are_equivalent
from src.automaton.simulator import simulate
from src.pipeline.evaluator import load_ground_truth
from src.regex.evaluator import evaluate_all, evaluate_text
from src.regex.parser import RegexFormatError, RegexResourceError, parse_regex, validate_regex
from src.regex.report import render_report
from src.regex.runner import build_prompt, run_pair
from src.regex.thompson import thompson
from src.testcases import TESTCASES


@pytest.mark.parametrize("text", ["0*1", "(0|1|2)2*", "(a|bb)*a", "0**", " (0 | 1) *\n"])
def test_valid(text):
    assert validate_regex(text, tuple("012ab"))


@pytest.mark.parametrize("text", ["", "()", "|0", "0|", "(0", "0)", "*0", "0||1", "[01]", "0+", "0?", "0{2}", "^0$", "ε", "∅", "0&1", "0.1", "```\n0\n```", "0#", "2", "ответ: 0"])
def test_invalid(text):
    assert not validate_regex(text, ("0", "1"))
    with pytest.raises(RegexFormatError):
        parse_regex(text, ("0", "1"))


def test_resource_limits_not_format_verdict():
    with pytest.raises(RegexResourceError):
        parse_regex("(" * 101 + "0" + ")" * 101, ("0", "1"))
    with pytest.raises(RegexResourceError):
        parse_regex("0" * 10001, ("0", "1"))
    assert evaluate_text("0" * 10001, "basic")["is_format_valid"] is None


@pytest.mark.parametrize("text", ["0", "0*", "(0*)*", "01|1", "0|11", "(0|1)*", "(01)*0", "(0*1*)*", "(0|11)*", "(0|1)(0|1)*", "(01|10)*", "((0|1)*01)*"])
def test_thompson_exhaustive_against_python(text):
    enfa = thompson(text, ("0", "1"))
    nfa = enfa.without_epsilon()
    assert enfa.n >= 2 and nfa.n == enfa.n
    for length in range(9):
        for chars in product("01", repeat=length):
            word = "".join(chars)
            assert simulate(nfa, list(map(int, word))) == bool(re.fullmatch(text, word))


def test_precedence():
    nfa = thompson("0|11*", ("0", "1")).without_epsilon()
    for word, expected in [("", False), ("0", True), ("1", True), ("11", True), ("01", False), ("00", False)]:
        assert simulate(nfa, list(map(int, word))) == expected


def _employer_expression():
    # Split the complement of the forbidden three-letter prefix at first mismatch.
    letters = "(A|M|C|S|P|B)"
    digits = "(0|1|2|3|4|5)"
    regions = f"((A|M|C|P|B){letters}{letters}|S(A|M|C|S|B){letters}|SP(A|M|C|S|P))"
    return f"({regions}{digits}|SPB(1|2|3|4|5)){digits}{digits}{digits}"


@pytest.mark.parametrize("case,text", [
    ("basic", "(1010)*1|010(1010)*"),
    ("4th-symbol", "(0|1)*1(0|1)(0|1)(0|1)"),
    ("intersection", "1*011*11|1*1(01|10)"),
    ("employer", _employer_expression()),
    ("personal", "(0|1(01*0)*1)*"),
])
def test_exact_ground_truth(case, text):
    case_data = TESTCASES[case]
    nfa = thompson(text, case_data.alphabet).without_epsilon()
    assert are_equivalent(nfa, load_ground_truth(case))
    assert evaluate_text(text, case)["is_correct"] is True


def test_iterated_kleene_star():
    assert are_equivalent(thompson("0**", ("0", "1")).without_epsilon(),
                          thompson("0*", ("0", "1")).without_epsilon())


def test_valid_but_wrong_language():
    r = evaluate_text("(0|1)*", "basic")
    assert r["is_format_valid"] is True
    assert r["is_correct"] is False


def test_evaluator_empty_raw_root(tmp_path):
    results = tmp_path / "results.jsonl"
    assert evaluate_all(tmp_path / "missing", results) == []
    assert results.read_text() == ""


def test_evaluator_preserves_raw_and_invalid_denominator(tmp_path):
    raw = tmp_path / "raw"
    target = raw / "model" / "4th-symbol"
    target.mkdir(parents=True)
    good = "(0|1)*1(0|1)(0|1)(0|1)"
    for i, text in enumerate([good, "", "[01]*"]):
        (target / f"run_{i:03d}.txt").write_text(text)
    rows = evaluate_all(raw, tmp_path / "result.jsonl")
    assert len(rows) == 3
    assert sum(r["is_correct"] for r in rows) == 1
    report = render_report(rows, [], ["model"])
    assert "33.3" in report
    assert "не завершён" in report
    assert (target / "run_000.txt").read_text() == good


def test_report_no_data_and_comparison():
    assert "Реальных ответов" in render_report([], [], ["model"])
    row = {"model": "model", "testcase": "basic", "length": 3, "is_format_valid": True, "is_correct": True}
    previous = {"model": "model", "testcase": "basic", "is_equivalent": False}
    report = render_report([row], [previous], ["model"])
    assert "+100.0" in report
    assert "лучше: регулярки" in report


def test_runner_resume_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr("src.regex.runner.time.sleep", lambda _: None)
    class FakeClient:
        calls = 0
        def generate(self, prompt):
            self.calls += 1
            assert TESTCASES["basic"].description in prompt
            return ""  # empty content is a real observed response, not a transport failure
    client = FakeClient()
    cfg = {"model_name": "example"}
    run_pair("model", cfg, "basic", 2, tmp_path, client)
    run_pair("model", cfg, "basic", 2, tmp_path, client)
    assert client.calls == 2
    metadata = json.loads((tmp_path / "model/basic/run_000.json").read_text())
    assert metadata["config"] == cfg
    assert metadata["prompt"] == build_prompt(TESTCASES["basic"])


def test_runner_transport_failure_is_not_a_response(tmp_path):
    class Broken:
        def generate(self, prompt):
            raise RuntimeError("offline")
    with pytest.raises(RuntimeError):
        run_pair("model", {}, "basic", 1, tmp_path, Broken())
    assert not list(tmp_path.rglob("run_*.txt"))
