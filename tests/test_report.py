import json

from src.metrics.aggregate import aggregate, load_results
from src.metrics.report import render_markdown_table, render_report


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


def test_render_markdown_table_contains_models_testcases_and_total_row():
    results = [
        _row("basic", "modelA", True, True, 3, True),
        _row("basic", "modelB", False, False, None, False),
    ]
    stats = aggregate(results)
    table = render_markdown_table(stats, ["modelA", "modelB"])

    assert "modelA" in table
    assert "modelB" in table
    assert "basic" in table
    assert "Всего" in table
    assert "100%" in table  # modelA: format_valid_pct
    assert "0%" in table  # modelB: format_valid_pct
    assert "—" in table  # modelB: avg_dfa_states отсутствует (None)


def test_render_report_writes_file_with_conclusions_placeholder(tmp_path):
    results_path = tmp_path / "runs.jsonl"
    with results_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(_row("basic", "modelA", True, True, 3, True), ensure_ascii=False) + "\n")

    out_path = tmp_path / "final_table.md"
    render_report(results_path=results_path, out_path=out_path)

    content = out_path.read_text(encoding="utf-8")
    assert "modelA" in content
    assert "Глубокомысленные выводы" in content


def test_load_results_skips_blank_lines(tmp_path):
    results_path = tmp_path / "runs.jsonl"
    results_path.write_text(
        json.dumps(_row("basic", "modelA", True, True, 3, True), ensure_ascii=False) + "\n\n",
        encoding="utf-8",
    )
    assert len(load_results(results_path)) == 1
