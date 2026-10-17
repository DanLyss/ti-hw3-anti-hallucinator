from pathlib import Path

from src.automaton.determinize import determinize
from src.automaton.parser import parse
from src.pipeline.evaluator import evaluate_all

FIXTURES = Path(__file__).parent / "fixtures"


def _make_data_raw(tmp_path: Path) -> Path:
    data_raw = tmp_path / "raw"
    out_dir = data_raw / "modelA" / "4th-symbol"
    out_dir.mkdir(parents=True)

    (out_dir / "run_000.txt").write_text((FIXTURES / "4th_symbol_correct.txt").read_text(), encoding="utf-8")
    (out_dir / "run_001.txt").write_text("это не автомат вообще", encoding="utf-8")
    (out_dir / "run_002.txt").write_text((FIXTURES / "4th_symbol_buggy.txt").read_text(), encoding="utf-8")
    return data_raw


def test_evaluate_all_handles_correct_broken_and_unparseable(tmp_path):
    data_raw = _make_data_raw(tmp_path)
    results_path = tmp_path / "results" / "runs.jsonl"

    results = evaluate_all(data_raw_root=data_raw, results_path=results_path)
    by_run = {r.run_id: r for r in results}

    assert set(by_run) == {"000", "001", "002"}

    correct = by_run["000"]
    expected_dfa_size = determinize(parse((FIXTURES / "4th_symbol_correct.txt").read_text())).n
    assert correct.is_format_valid is True
    assert correct.is_deterministic is False  # (0,1) -> {0,1}, две цели — это NFA
    assert correct.dfa_state_count == expected_dfa_size
    assert correct.is_simulation_correct is True
    assert correct.is_equivalent is True  # домашка 5: эквивалентен минимальному ground truth DFA
    assert correct.min_dfa_state_count == 16  # 2^4 — минимальный DFA для 4th-symbol

    unparseable = by_run["001"]
    assert unparseable.is_format_valid is False
    assert unparseable.format_violations  # список нарушений непустой
    assert unparseable.is_deterministic is None
    assert unparseable.dfa_state_count is None
    assert unparseable.is_simulation_correct is None
    assert unparseable.is_equivalent is None
    assert unparseable.min_dfa_state_count is None

    buggy = by_run["002"]
    assert buggy.is_format_valid is True  # структурно корректен, просто не та автоматика
    assert buggy.is_simulation_correct is False
    assert buggy.is_equivalent is False


def test_evaluate_all_writes_results_file(tmp_path):
    data_raw = _make_data_raw(tmp_path)
    results_path = tmp_path / "results" / "runs.jsonl"

    evaluate_all(data_raw_root=data_raw, results_path=results_path)

    lines = results_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
