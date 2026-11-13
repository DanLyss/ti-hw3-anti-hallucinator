"""Collect original model answers; resume completed requests without spending twice."""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.pipeline.runner import PROJECT_ROOT, _build_client
from src.testcases import TESTCASES

RAW_ROOT = PROJECT_ROOT / "data/raw_regex"


def build_prompt(testcase):
    return (
        "Построй регулярное выражение для следующего языка:\n"
        + testcase.description
        + "\n\nДопустимы ТОЛЬКО символы алфавита, конкатенация, альтернатива |, "
        "звезда Клини * и круглые скобки. Приоритет: * выше конкатенации, "
        "конкатенация выше |. Алфавит: " + ", ".join(testcase.alphabet)
        + ". Нельзя использовать ε, ∅, +, ?, классы [], степени {}, якоря, "
        "пересечение, отрицание или другие сокращения. "
        "Верни только выражение, без пояснений и без Markdown."
    )


def run_pair(name, cfg, testcase_id, runs, out_root=RAW_ROOT, client=None):
    client = client or _build_client(cfg)
    target = out_root / name / testcase_id
    target.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(TESTCASES[testcase_id])
    for i in range(runs):
        path = target / f"run_{i:03d}.txt"
        if path.exists():
            continue  # even an empty answer is an observed result
        started = datetime.now(timezone.utc).isoformat()
        answer = client.generate(prompt)  # HTTP errors are not model answers
        metadata = {"model": name, "config": cfg, "testcase": testcase_id,
                    "prompt": prompt, "started_at": started,
                    "completed_at": datetime.now(timezone.utc).isoformat()}
        # Write metadata first; the answer file is the completion marker.
        path.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        path.write_text(answer, encoding="utf-8")
        print(f"{name}/{testcase_id}/{i}: {len(answer)} chars", flush=True)
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20, choices=range(20, 51))
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    config = yaml.safe_load((PROJECT_ROOT / "config/models.yaml").read_text(encoding="utf-8"))
    # Same four models as the one-way automaton experiment; fifth is 2DFA-only.
    models = {name: cfg for name, cfg in config["models"].items() if not cfg.get("only_2dfa")}
    failures = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(run_pair, name, cfg, case, args.runs): (name, case)
                   for name, cfg in models.items() for case in TESTCASES}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                pair = futures[future]
                failures.append(pair)
                # Do not print HTTP exception bodies, credentials or provider URLs.
                print(f"FAILED {pair}: {type(exc).__name__}", flush=True)
    if failures:
        raise SystemExit(f"incomplete experiment: {failures}")


if __name__ == "__main__":
    main()
