import json
import shutil
import subprocess
import sys

import pytest

from eval.run import ROOT


@pytest.fixture
def dataset(tmp_path):
    target = tmp_path / "data"
    shutil.copytree(ROOT / "data/dev", target)
    return target


def invoke(directory):
    return subprocess.run(
        [sys.executable, "-B", "-m", "eval.final", "--directory", str(directory), "--mode", "off"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_refuses_second_run(dataset):
    assert invoke(dataset).returncode == 0
    result = invoke(dataset)
    assert result.returncode != 0
    assert json.loads(result.stdout)["error"] == "already_run"


def test_outputs_metrics_without_case_text(dataset):
    path = dataset / "cases/clean-1.json"
    data = json.loads(path.read_text())
    secret = "PRIVATE-SYNTHETIC-SENTINEL-948153"
    data["versions"][0]["text"] = secret
    path.write_text(json.dumps(data))
    before = {
        p: p.read_bytes()
        for folder in ("detect", "eval", "data/dev")
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    result = invoke(dataset)
    assert result.returncode == 0, result.stdout
    assert secret not in result.stdout + result.stderr
    for filename in (".lexcheck-run.json", "final-manifest.json", "final-results.json"):
        assert secret not in (dataset / filename).read_text()
    assert all(path.read_bytes() == content for path, content in before.items())
    manifest = json.loads((dataset / "final-manifest.json").read_text())
    assert manifest["git_sha"] and len(manifest["input_hashes"]) == 16


def test_bad_labels_do_not_consume(dataset):
    (dataset / "answers.json").write_text("private malformed text")
    result = invoke(dataset)
    assert result.returncode != 0
    assert "private malformed" not in result.stdout + result.stderr
    assert json.loads(invoke(dataset).stdout)["error"] == "invalid_dataset"
    assert not (dataset / ".lexcheck-run.json").exists()


def test_rejects_repository_directory():
    result = invoke(ROOT / "data/dev")
    assert json.loads(result.stdout)["error"] == "directory_inside_repository"


def test_exclusive_run_concurrent(dataset):
    from concurrent.futures import ThreadPoolExecutor

    from eval.final import run

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda d: run(d, mode="off"), (dataset, dataset)))
    assert sorted(code for _, code in results) == [0, 2]
    assert [output.get("error") for output, code in results if code == 2] == ["already_run"]


def test_final_direct_invalid_and_missing(dataset, tmp_path):
    from eval.final import run

    assert run(tmp_path / "absent")[0]["error"] == "directory_missing"
    assert run(ROOT / "data/dev")[0]["error"] == "directory_inside_repository"
    (dataset / "answers.json").write_text("{}")
    assert run(dataset, mode="off")[0]["error"] == "invalid_dataset"
    assert not (dataset / "final-manifest.json").exists()


def test_rejects_linked_input(dataset, tmp_path):
    from eval.final import run

    path = dataset / "cases/clean-1.json"
    source = tmp_path / "source.json"
    path.rename(source)
    path.symlink_to(source)
    assert run(dataset, mode="off")[0]["error"] == "invalid_dataset"


def test_main_prints_aggregate(dataset, capsys):
    from eval.final import main

    assert main(["--directory", str(dataset), "--mode", "off"]) == 0
    assert json.loads(capsys.readouterr().out)["n"] == 15


def test_check_does_not_consume(dataset):
    from eval.final import run

    output, code = run(dataset, mode="off", check_only=True)
    assert code == 0 and output["n"] == 15
    assert not (dataset / ".lexcheck-run.json").exists()
    assert run(dataset, mode="off")[1] == 0


def test_mode_is_required(dataset):
    from eval.final import run

    assert run(dataset)[0]["error"] == "mode_required"


def test_dirty_tree_refused(dataset, monkeypatch):
    from eval.final import _manifest, run

    monkeypatch.setenv("OPENAI_MODEL", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-credential")
    original = _manifest
    monkeypatch.setattr(
        "eval.final._manifest", lambda inputs, mode: {**original(inputs, mode), "dirty": True}
    )
    assert run(dataset, mode="live")[0]["error"] == "dirty_tree"
    assert not (dataset / ".lexcheck-run.json").exists()


def test_failed_evaluation_still_consumes(dataset, monkeypatch):
    from eval.final import run

    def failed(*args, **kwargs):
        raise RuntimeError("private input")

    monkeypatch.setattr("eval.final.evaluate_cases", failed)
    assert run(dataset, mode="off")[0]["error"] == "run_failed"
    assert run(dataset, mode="off")[0]["error"] == "already_run"
