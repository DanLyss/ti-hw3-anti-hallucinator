import json
from functools import lru_cache
from pathlib import Path

from src.automaton.determinize import TooManyStatesError, determinize
from src.automaton.equivalence import are_equivalent
from src.automaton.simulator import simulate
from src.pipeline.evaluator import load_ground_truth
from src.pipeline.runner import PROJECT_ROOT
from src.regex.parser import RegexFormatError, RegexResourceError, parse_regex
from src.regex.runner import RAW_ROOT
from src.regex.thompson import from_tree
from src.testcases import TESTCASES

RESULTS = PROJECT_ROOT / "data/results/runs_regex.jsonl"


@lru_cache(maxsize=512)
def evaluate_text(text, testcase_id):
    case = TESTCASES[testcase_id]
    result = {"length": len("".join(text.split())), "is_format_valid": None,
              "is_correct": None, "error": None, "nfa_states": None, "dfa_states": None,
              "counterexample": None}
    try:
        tree = parse_regex(text, case.alphabet)
    except RegexFormatError as exc:
        result.update(is_format_valid=False, is_correct=False, error=str(exc))
        return result
    except (RegexResourceError, RecursionError) as exc:
        result["error"] = str(exc)
        return result
    result["is_format_valid"] = True
    try:
        enfa = from_tree(tree, case.alphabet)
        result["nfa_states"] = enfa.n
        nfa = enfa.without_epsilon()
        truth = load_ground_truth(testcase_id)
        # A mismatching word is an exact proof of non-equivalence, even if the
        # full subset construction would exceed the state limit. Agreement on
        # this finite set is never treated as proof of equivalence.
        for word in dict.fromkeys(["", *(w for w, _ in case.sample_strings())]):
            encoded = case.encode(word)
            if simulate(nfa, encoded) != simulate(truth, encoded):
                result.update(is_correct=False, counterexample=word)
                return result
        dfa = determinize(nfa)
        result["dfa_states"] = dfa.n
        result["is_correct"] = are_equivalent(dfa, truth)
    except (TooManyStatesError, RecursionError) as exc:
        result["error"] = type(exc).__name__
    return result


def evaluate_all(raw_root: Path = RAW_ROOT, results_path: Path = RESULTS):
    rows = []
    for path in sorted(raw_root.glob("*/*/run_*.txt")):
        model, case = path.parent.parent.name, path.parent.name
        if case not in TESTCASES:
            continue
        rows.append({"model": model, "testcase": case, "run_id": path.stem,
                     "raw_file_path": path.relative_to(raw_root).as_posix(),
                     **evaluate_text(path.read_text(encoding="utf-8"), case)})
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return rows


if __name__ == "__main__":
    evaluate_all()
