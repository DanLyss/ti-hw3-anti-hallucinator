import sys
import time
from datetime import datetime
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
OUTAGE_PAUSE_SECONDS = 60.0
MAX_FAILURES_IN_ROW = 30  # ~полчаса без сети подряд — тогда сдаёмся (перезапуск продолжит с места)


def _log(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


def run_testcase(
    model_name: str,
    client: LLMClient,
    testcase_id: str,
    runs: int,
    out_root: Path = DEFAULT_DATA_RAW_2DFA,
    pacing_seconds: float = REQUEST_PACING_SECONDS,
    outage_pause_seconds: float = OUTAGE_PAUSE_SECONDS,
) -> None:
    """Один запрос — один тесткейс. Ответ пишется как есть в
    data/raw_2dfa/<model>/<testcase>/run_XXX.txt, уже собранные прогоны пропускаются.

    Рассчитан на нестабильный интернет: клиент сам ретраит короткие сбои (~30 с), а если
    сеть пропала надолго, здесь ждём outage_pause_seconds и повторяем тот же запрос, пока
    не наберётся MAX_FAILURES_IN_ROW неудач подряд."""
    testcase = TESTCASES_2DFA[testcase_id]
    out_dir = out_root / model_name / testcase_id
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt_2dfa(testcase.description, testcase.alphabet)
    for run_id in range(runs):
        out_path = out_dir / f"run_{run_id:03d}.txt"
        if out_path.exists():
            continue
        for failures in range(1, MAX_FAILURES_IN_ROW + 1):
            try:
                response = client.generate(prompt)
                break
            except Exception as exc:  # сеть/провайдер — ждём и повторяем тот же запрос
                _log(f"{model_name}/{testcase_id} run {run_id}: ошибка {failures}/{MAX_FAILURES_IN_ROW}: {exc!r}")
                if failures == MAX_FAILURES_IN_ROW:
                    raise
                time.sleep(outage_pause_seconds)
        out_path.write_text(response, encoding="utf-8")
        _log(f"{model_name}/{testcase_id} run {run_id}: ok ({len(response)} символов)")
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
        futures = {pool.submit(run_testcase, name, client, tc, runs, out_root, pacing_seconds): (name, tc) for name, client, tc in jobs}
        for future, (name, tc) in futures.items():
            try:
                future.result()
            except Exception as exc:  # одна сломанная пара не останавливает остальные
                _log(f"{name}/{tc}: сдался после {MAX_FAILURES_IN_ROW} неудач подряд: {exc!r}")
    _log("прогон завершён")


def main(runs: int = RUNS_PER_TESTCASE_2DFA) -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    config = yaml.safe_load((PROJECT_ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    clients = {name: _build_client(cfg) for name, cfg in config["models"].items()}
    run_all_2dfa(clients, runs=runs)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else RUNS_PER_TESTCASE_2DFA)
