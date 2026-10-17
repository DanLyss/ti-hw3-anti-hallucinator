from pathlib import Path
from typing import Callable

from src.metrics.aggregate import (
    TOTAL_ROW,
    DEFAULT_RESULTS_PATH,
    TestcaseModelStats,
    aggregate,
    load_results,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "final_table.md"

_METRICS: list[tuple[str, Callable[[TestcaseModelStats], str]]] = [
    ("Корректные по формату, %", lambda s: f"{s.format_valid_pct:.0f}%"),
    ("Детерминированные, %", lambda s: f"{s.deterministic_pct:.0f}%"),
    ("Среднее число состояний в DFA", lambda s: f"{s.avg_dfa_states:.1f}" if s.avg_dfa_states is not None else "—"),
    ("Корректные по симуляции, %", lambda s: f"{s.simulation_correct_pct:.0f}%"),
    ("Среднее число состояний в минимизированном DFA", lambda s: f"{s.avg_min_dfa_states:.1f}" if s.avg_min_dfa_states is not None else "—"),
    ("Корректные автоматы, %", lambda s: f"{s.equivalent_pct:.0f}%"),
]


def render_markdown_table(stats: list[TestcaseModelStats], models: list[str]) -> str:
    lookup = {(s.testcase, s.model): s for s in stats}
    testcases = sorted({s.testcase for s in stats if s.testcase != TOTAL_ROW})

    header = ["Тесткейс"] + [f"{metric_name} ({model})" for metric_name, _ in _METRICS for model in models]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]

    for testcase in [*testcases, TOTAL_ROW]:
        row = [testcase]
        for _, fmt in _METRICS:
            for model in models:
                stat = lookup.get((testcase, model))
                row.append(fmt(stat) if stat is not None else "—")
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def render_report(
    results_path: Path = DEFAULT_RESULTS_PATH,
    out_path: Path = DEFAULT_REPORT_PATH,
) -> None:
    results = load_results(results_path)
    models = sorted({r["model"] for r in results})
    stats = aggregate(results)
    table = render_markdown_table(stats, models)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "# Итоговая таблица метрик\n\n"
        f"{table}\n\n"
        "## Глубокомысленные выводы\n\n"
        "_TODO: дописать руками после анализа таблицы (см. ARCHITECTURE.md §4)._\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    render_report()
