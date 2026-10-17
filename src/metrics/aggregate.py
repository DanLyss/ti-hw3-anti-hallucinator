import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "data" / "results" / "runs.jsonl"

TOTAL_ROW = "Всего"


@dataclass
class TestcaseModelStats:
    testcase: str
    model: str
    total_runs: int
    format_valid_pct: float
    deterministic_pct: float
    avg_dfa_states: float | None
    simulation_correct_pct: float
    avg_min_dfa_states: float | None = None
    equivalent_pct: float = 0.0


def load_results(results_path: Path = DEFAULT_RESULTS_PATH) -> list[dict]:
    with results_path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _stats_for(testcase: str, model: str, rows: list[dict]) -> TestcaseModelStats:
    total = len(rows)
    format_valid = sum(1 for r in rows if r["is_format_valid"])
    deterministic = sum(1 for r in rows if r["is_deterministic"])
    sim_correct = sum(1 for r in rows if r["is_simulation_correct"])
    dfa_sizes = [r["dfa_state_count"] for r in rows if r["dfa_state_count"] is not None]
    avg_dfa = sum(dfa_sizes) / len(dfa_sizes) if dfa_sizes else None
    min_sizes = [r["min_dfa_state_count"] for r in rows if r.get("min_dfa_state_count") is not None]
    equivalent = sum(1 for r in rows if r.get("is_equivalent"))
    return TestcaseModelStats(
        testcase=testcase,
        model=model,
        total_runs=total,
        format_valid_pct=100 * format_valid / total,
        deterministic_pct=100 * deterministic / total,
        avg_dfa_states=avg_dfa,
        simulation_correct_pct=100 * sim_correct / total,
        avg_min_dfa_states=sum(min_sizes) / len(min_sizes) if min_sizes else None,
        equivalent_pct=100 * equivalent / total,
    )


def aggregate(results: list[dict]) -> list[TestcaseModelStats]:
    """Группирует по (тесткейс, модель) + добавляет строку "Всего" (агрегат по всем
    тесткейсам на модель)."""
    by_testcase_model: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_testcase_model[(r["testcase"], r["model"])].append(r)
        by_model[r["model"]].append(r)

    stats = [_stats_for(testcase, model, rows) for (testcase, model), rows in sorted(by_testcase_model.items())]
    stats += [_stats_for(TOTAL_ROW, model, rows) for model, rows in sorted(by_model.items())]
    return stats
