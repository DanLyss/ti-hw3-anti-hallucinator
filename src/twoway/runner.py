import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.llm_clients.base import LLMClient
from src.pipeline.runner import PROJECT_ROOT, REQUEST_PACING_SECONDS, _build_client
from src.twoway.prompt_builder import build_prompt_2dfa
from src.twoway.testcases import TESTCASES_2DFA

DEFAULT_DATA_RAW_2DFA = PROJECT_ROOT / "data" / "raw_2dfa"
RUNS_PER_TESTCASE_2DFA = 20  # листок: не менее 20 запросов на тесткейс


def run_testcase(
    model_name: str,
    client: LLMClient,
    testcase_id: str,
    runs: int,
    out_root: Path = DEFAULT_DATA_RAW_2DFA,
    pacing_seconds: float = REQUEST_PACING_SECONDS,
) -> None:
    """Один запрос — один тесткейс. Ответ пишется как есть в
    data/raw_2dfa/<model>/<testcase>/run_XXX.txt, уже собранные прогоны пропускаются."""
    testcase = TESTCASES_2DFA[testcase_id]
    out_dir = out_root / model_name / testcase_id
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt_2dfa(testcase.description, testcase.alphabet)
    for run_id in range(runs):
        out_path = out_dir / f"run_{run_id:03d}.txt"
        if out_path.exists():
            continue
        out_path.write_text(client.generate(prompt), encoding="utf-8")
        time.sleep(pacing_seconds)


def run_all_2dfa(
    clients: dict[str, LLMClient],
    runs: int = RUNS_PER_TESTCASE_2DFA,
    out_root: Path = DEFAULT_DATA_RAW_2DFA,
    pacing_seconds: float = REQUEST_PACING_SECONDS,
) -> None:
    """Параллельно по парам (модель, тесткейс): reasoning-модели отвечают десятки секунд,
    последовательный прогон занял бы часы (см. домашку 3)."""
    jobs = [(name, client, tc) for name, client in clients.items() for tc in TESTCASES_2DFA]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [pool.submit(run_testcase, name, client, tc, runs, out_root, pacing_seconds) for name, client, tc in jobs]
        for future in futures:
            future.result()


def main(runs: int = RUNS_PER_TESTCASE_2DFA) -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    config = yaml.safe_load((PROJECT_ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    clients = {name: _build_client(cfg) for name, cfg in config["models"].items()}
    run_all_2dfa(clients, runs=runs)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else RUNS_PER_TESTCASE_2DFA)
