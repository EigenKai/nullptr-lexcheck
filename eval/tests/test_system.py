import ast
import json
import socket

from contracts.models import EvaluationReport
from eval.run import ROOT, main


def test_offline_eval_system(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "off")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    main()
    path = ROOT / "eval/results/latest.json"
    report = EvaluationReport.model_validate_json(path.read_text())
    assert report.n == 15
    assert len(report.systems) == 3
    before = path.read_bytes()
    main()
    assert before == path.read_bytes()
    labels = json.loads((ROOT / "data/dev/answers.json").read_text())["cases"]
    assert sum(v["is_clean"] for v in labels.values()) >= 5
    assert all(v["label_status"] == "draft_pending_owner_review" for v in labels.values())


def test_only_client_imports_sdk():
    for folder in ("detect", "eval"):
        for path in (ROOT / folder).rglob("*.py"):
            tree = ast.parse(path.read_text())
            imports = [
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            ]
            imports += [
                node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
            ]
            if any(name.split(".")[0] == "openai" for name in imports):
                assert path == ROOT / "detect/client.py"
