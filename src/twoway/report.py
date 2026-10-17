import json
from collections import defaultdict
from pathlib import Path

from src.pipeline.runner import PROJECT_ROOT
from src.twoway.evaluator import DEFAULT_RESULTS_PATH_2DFA

DEFAULT_REPORT_PATH_2DFA = PROJECT_ROOT / "reports" / "final_table_2dfa.md"
TOTAL_ROW = "total"


def _pct(rows: list[dict], key: str) -> str:
    return f"{100 * sum(1 for r in rows if r[key]) / len(rows):.0f}%"


def _avg(rows: list[dict], key: str) -> str:
    values = [r[key] for r in rows if r[key] is not None]
    return f"{sum(values) / len(values):.1f}" if values else "—"


# Колонки — как в табличке листка (плюс размер минимизированного DFA из части 1).
METRICS = [
    ("Корректные по формату, %", lambda rows: _pct(rows, "is_format_valid")),
    ("Действительно 2DFA, %", lambda rows: _pct(rows, "is_really_2dfa")),
    ("Среднее количество состояний в 2DFA", lambda rows: _avg(rows, "state_count")),
    ("Среднее количество состояний в DFA", lambda rows: _avg(rows, "dfa_state_count")),
    ("Среднее количество состояний в минимизированном DFA", lambda rows: _avg(rows, "min_dfa_state_count")),
    ("Корректные автоматы, %", lambda rows: _pct(rows, "is_correct")),
]


def render_table_2dfa(results: list[dict]) -> str:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in results:
        groups[(r["testcase"], r["model"])].append(r)
        groups[(TOTAL_ROW, r["model"])].append(r)
    models = sorted({r["model"] for r in results})
    testcases = sorted({r["testcase"] for r in results}) + [TOTAL_ROW]

    header = ["Тесткейс"] + [f"{name} ({model})" for name, _ in METRICS for model in models]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for testcase in testcases:
        cells = [fmt(groups[(testcase, model)]) if groups.get((testcase, model)) else "—" for _, fmt in METRICS for model in models]
        lines.append("| " + " | ".join([testcase, *cells]) + " |")
    return "\n".join(lines)


def render_report_2dfa(results_path: Path = DEFAULT_RESULTS_PATH_2DFA, out_path: Path = DEFAULT_REPORT_PATH_2DFA) -> None:
    """Перезаписывает только таблицу, раздел с выводами (если он уже есть) сохраняется."""
    with results_path.open(encoding="utf-8") as f:
        results = [json.loads(line) for line in f if line.strip()]
    table = render_table_2dfa(results)
    conclusions = "## Глубокомысленные выводы\n\n_TODO_\n"
    if out_path.exists():
        old = out_path.read_text(encoding="utf-8")
        if "## Глубокомысленные выводы" in old:
            conclusions = old[old.index("## Глубокомысленные выводы"):]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(f"# Итоговая таблица метрик: 2DFA\n\n{table}\n\n{conclusions}", encoding="utf-8")


if __name__ == "__main__":
    render_report_2dfa()
