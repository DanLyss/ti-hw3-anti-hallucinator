from src.llm_clients.base import LLMClient
from src.pipeline.runner import run_for_model
from src.testcases import TESTCASES


class _FakeClient(LLMClient):
    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return "fake response"


def test_run_for_model_writes_one_file_per_run(tmp_path):
    client = _FakeClient()
    run_for_model("fake-model", client, runs_per_testcase=2, out_root=tmp_path)

    for testcase_id in TESTCASES:
        out_dir = tmp_path / "fake-model" / testcase_id
        files = sorted(p.name for p in out_dir.glob("run_*.txt"))
        assert files == ["run_000.txt", "run_001.txt"]
        assert (out_dir / "run_000.txt").read_text(encoding="utf-8") == "fake response"

    assert client.calls == 2 * len(TESTCASES)


def test_run_for_model_skips_already_collected_runs(tmp_path):
    client = _FakeClient()
    first_testcase_id = next(iter(TESTCASES))
    out_dir = tmp_path / "fake-model" / first_testcase_id
    out_dir.mkdir(parents=True)
    (out_dir / "run_000.txt").write_text("already here", encoding="utf-8")

    run_for_model("fake-model", client, runs_per_testcase=2, out_root=tmp_path)

    assert (out_dir / "run_000.txt").read_text(encoding="utf-8") == "already here"
    assert client.calls == 2 * len(TESTCASES) - 1
