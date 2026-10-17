import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.automaton.equivalence import are_equivalent
from src.automaton.minimize import minimize
from src.automaton.parser import ParseError
from src.pipeline.runner import PROJECT_ROOT
from src.twoway.parser import parse_two_way
from src.twoway.runner import DEFAULT_DATA_RAW_2DFA
from src.twoway.testcases import TESTCASES_2DFA, ground_truth_min_dfa
from src.twoway.to_dfa import TooManyStatesError, two_way_to_dfa
from src.twoway.validator import is_deterministic_two_way, is_really_2dfa, validate_two_way

DEFAULT_RESULTS_PATH_2DFA = PROJECT_ROOT / "data" / "results" / "runs_2dfa.jsonl"


@dataclass
class TwoWayRunResult:
    model: str
    testcase: str
    run_id: str
    is_format_valid: bool
    format_violations: list[str]
    is_really_2dfa: bool | None
    state_count: int | None  # n самого 2DFA
    dfa_state_count: int | None  # после 2DFA -> DFA (достижимые пары (q̂, f) + мёртвое)
    min_dfa_state_count: int | None
    is_correct: bool | None  # DFA эквивалентен минимальному ground truth DFA
    raw_file_path: str


def evaluate_file_2dfa(model: str, testcase_id: str, run_id: str, path: Path) -> TwoWayRunResult:
    """Как и в домашке 3, проверки независимы: невалидный формат не мешает попытаться
    сконвертировать автомат. Недетерминированный ответ (2NFA) в DFA не переводим — в лекции
    построение только для 2DFA — и считаем некорректным."""
    testcase = TESTCASES_2DFA[testcase_id]
    try:
        automaton = parse_two_way(path.read_text(encoding="utf-8"))
    except ParseError as exc:
        return TwoWayRunResult(model, testcase_id, run_id, False, exc.violations, None, None, None, None, None, str(path))

    is_valid, violations = validate_two_way(automaton, expected_alphabet_size=len(testcase.alphabet))
    dfa_states = min_states = None
    is_correct = False
    if is_deterministic_two_way(automaton):
        try:
            dfa = two_way_to_dfa(automaton)
            dfa_states, min_states = dfa.n, minimize(dfa).n
            is_correct = are_equivalent(dfa, ground_truth_min_dfa(testcase_id))
        except TooManyStatesError:
            is_correct = None
    return TwoWayRunResult(
        model, testcase_id, run_id, is_valid, violations, is_really_2dfa(automaton),
        automaton.n, dfa_states, min_states, is_correct, str(path),
    )


def evaluate_all_2dfa(
    data_raw_root: Path = DEFAULT_DATA_RAW_2DFA,
    results_path: Path = DEFAULT_RESULTS_PATH_2DFA,
) -> list[TwoWayRunResult]:
    results = [
        evaluate_file_2dfa(model_dir.name, testcase_dir.name, run_file.stem.removeprefix("run_"), run_file)
        for model_dir in sorted(p for p in data_raw_root.iterdir() if p.is_dir())
        for testcase_dir in sorted(p for p in model_dir.iterdir() if p.is_dir() and p.name in TESTCASES_2DFA)
        for run_file in sorted(testcase_dir.glob("run_*.txt"))
    ]
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    return results


if __name__ == "__main__":
    evaluate_all_2dfa()
