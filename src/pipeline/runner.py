import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.llm_clients.base import LLMClient
from src.llm_clients.deepseek_client import DeepSeekClient
from src.llm_clients.openai_client import OpenAIClient
from src.llm_clients.qwen_client import QwenClient
from src.prompt_builder import build_prompt
from src.testcases import TESTCASES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_RAW = PROJECT_ROOT / "data" / "raw"


def run_for_model(
    model_name: str,
    client: LLMClient,
    runs_per_testcase: int,
    out_root: Path = DEFAULT_DATA_RAW,
) -> None:
    for testcase_id, testcase in TESTCASES.items():
        out_dir = out_root / model_name / testcase_id
        out_dir.mkdir(parents=True, exist_ok=True)
        prompt = build_prompt(testcase.description, testcase.alphabet)
        for run_id in range(runs_per_testcase):
            out_path = out_dir / f"run_{run_id:03d}.txt"
            if out_path.exists():
                continue  # не тратим платные запросы повторно на уже собранный прогон
            response = client.generate(prompt)
            out_path.write_text(response, encoding="utf-8")


def run_all(
    clients: dict[str, LLMClient],
    runs_per_testcase: int = 50,
    out_root: Path = DEFAULT_DATA_RAW,
) -> None:
    for model_name, client in clients.items():
        run_for_model(model_name, client, runs_per_testcase, out_root)


def _build_client(cfg: dict) -> LLMClient:
    provider = cfg["provider"]
    temperature = cfg.get("temperature", 0.7)
    max_tokens = cfg.get("max_tokens", 4096)
    # base_url можно переопределить прямо в config/models.yaml, не трогая код — например,
    # чтобы дёргать Qwen через агрегатор вроде OpenRouter вместо прямого DashScope API.
    base_url_override = cfg.get("base_url")
    if provider == "openai":
        kwargs = {"base_url": base_url_override} if base_url_override else {}
        return OpenAIClient(
            api_key=os.environ["OPENAI_API_KEY"],
            model_name=cfg["model_name"],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    if provider == "deepseek":
        kwargs = {"base_url": base_url_override} if base_url_override else {}
        return DeepSeekClient(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            model_name=cfg["model_name"],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    if provider == "qwen":
        kwargs = {"base_url": base_url_override} if base_url_override else {}
        return QwenClient(
            api_key=os.environ["QWEN_API_KEY"],
            model_name=cfg["model_name"],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    raise ValueError(f"неизвестный provider в config/models.yaml: {provider}")


def main() -> None:
    load_dotenv()
    config = yaml.safe_load((PROJECT_ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    clients = {name: _build_client(cfg) for name, cfg in config["models"].items()}
    run_all(clients, runs_per_testcase=config.get("runs_per_testcase", 50))


if __name__ == "__main__":
    main()
