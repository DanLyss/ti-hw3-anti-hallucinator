import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.automaton.determinize import TooManyStatesError, determinize
from src.automaton.parser import ParseError, parse
from src.automaton.simulator import check_correctness
from src.automaton.validator import is_deterministic, validate
from src.testcases import TESTCASES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_RAW = PROJECT_ROOT / "data" / "raw"
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "data" / "results" / "runs.jsonl"


@dataclass
class RunResult:
    model: str
    testcase: str
    run_id: str
    is_format_valid: bool
    format_violations: list[str]
    is_deterministic: bool | None
    dfa_state_count: int | None
    is_simulation_correct: bool | None
    raw_file_path: str


def evaluate_file(model: str, testcase_id: str, run_id: str, path: Path) -> RunResult:
    """Прогоняет один сырой ответ модели через все три проверки из ПДФ независимо —
    ParseError блокирует всё (нет структуры для анализа), а провал format-валидации
    не мешает всё равно посчитать симуляцию/детерминизацию (см. ARCHITECTURE.md §1)."""
    text = path.read_text(encoding="utf-8")
    testcase = TESTCASES[testcase_id]

    try:
        automaton = parse(text)
    except ParseError as exc:
        return RunResult(model, testcase_id, run_id, False, exc.violations, None, None, None, str(path))

    is_valid, violations = validate(automaton, expected_alphabet_size=len(testcase.alphabet))
    deterministic = is_deterministic(automaton)

    try:
        dfa_state_count = determinize(automaton).n
    except TooManyStatesError:
        dfa_state_count = None

    samples = [(testcase.encode(w), label) for w, label in testcase.sample_strings()]
    is_correct = check_correctness(automaton, samples)

    return RunResult(model, testcase_id, run_id, is_valid, violations, deterministic, dfa_state_count, is_correct, str(path))


def evaluate_all(
    data_raw_root: Path = DEFAULT_DATA_RAW,
    results_path: Path = DEFAULT_RESULTS_PATH,
) -> list[RunResult]:
    results: list[RunResult] = []
    for model_dir in sorted(p for p in data_raw_root.iterdir() if p.is_dir()):
        for testcase_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
            if testcase_dir.name not in TESTCASES:
                continue
            for run_file in sorted(testcase_dir.glob("run_*.txt")):
                run_id = run_file.stem.removeprefix("run_")
                results.append(evaluate_file(model_dir.name, testcase_dir.name, run_id, run_file))

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    return results


if __name__ == "__main__":
    evaluate_all()
