import pytest

from src.metrics.aggregate import TOTAL_ROW, aggregate


def _row(testcase, model, is_format_valid, is_deterministic, dfa_state_count, is_simulation_correct):
    return {
        "model": model,
        "testcase": testcase,
        "run_id": "000",
        "is_format_valid": is_format_valid,
        "format_violations": [],
        "is_deterministic": is_deterministic,
        "dfa_state_count": dfa_state_count,
        "is_simulation_correct": is_simulation_correct,
        "raw_file_path": "x",
    }


def test_aggregate_computes_percentages_per_testcase_and_model():
    results = [
        _row("basic", "modelA", True, True, 3, True),
        _row("basic", "modelA", True, False, 5, False),
        _row("basic", "modelA", False, False, None, False),
        _row("4th-symbol", "modelA", True, True, 2, True),
    ]
    stats = aggregate(results)
    by_key = {(s.testcase, s.model): s for s in stats}

    basic = by_key[("basic", "modelA")]
    assert basic.total_runs == 3
    assert basic.format_valid_pct == pytest.approx(200 / 3)
    assert basic.deterministic_pct == pytest.approx(100 / 3)
    assert basic.avg_dfa_states == 4.0  # среднее по двум непустым значениям (3, 5), None игнорируется
    assert basic.simulation_correct_pct == pytest.approx(100 / 3)


def test_aggregate_adds_total_row_per_model():
    results = [
        _row("basic", "modelA", True, True, 2, True),
        _row("4th-symbol", "modelA", False, False, None, False),
    ]
    stats = aggregate(results)
    by_key = {(s.testcase, s.model): s for s in stats}

    total = by_key[(TOTAL_ROW, "modelA")]
    assert total.total_runs == 2
    assert total.format_valid_pct == 50.0
    assert total.avg_dfa_states == 2.0


def test_aggregate_handles_all_dfa_sizes_missing():
    results = [_row("basic", "modelA", False, False, None, False)]
    stats = aggregate(results)
    assert stats[0].avg_dfa_states is None
