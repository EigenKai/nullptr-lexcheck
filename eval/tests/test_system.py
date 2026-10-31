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


def test_parallel_eval_matches_sequential(monkeypatch):
    from types import SimpleNamespace

    from detect.candidates import CandidateBatch
    from detect.client import ModelClient
    from eval.run import evaluate_cases, load_cases

    client = ModelClient(
        model="test",
        transport=lambda **kw: SimpleNamespace(
            status="completed", output_parsed=CandidateBatch(candidates=())
        ),
    )
    cases = load_cases(ROOT / "data/dev")
    monkeypatch.setenv("LEXCHECK_EVAL_WORKERS", "1")
    sequential, trace1 = evaluate_cases(cases, mode="live", client=client)
    monkeypatch.setenv("LEXCHECK_EVAL_WORKERS", "4")
    parallel, trace4 = evaluate_cases(tuple(reversed(cases)), mode="live", client=client)

    def without_latency(report):
        return report.model_copy(
            update={
                "systems": tuple(s.model_copy(update={"latency_ms": None}) for s in report.systems)
            }
        )

    assert without_latency(sequential) == without_latency(parallel)
    assert trace1 == trace4


def test_trace_counts_errors_by_system():
    from detect.client import ModelClient
    from eval.run import evaluate_cases, load_cases

    def failed(**kwargs):
        raise RuntimeError("private")

    _, trace = evaluate_cases(
        load_cases(ROOT / "data/dev")[:1],
        mode="live",
        client=ModelClient(model="test", transport=failed),
    )
    assert trace[-1]["errors"]["plain_chat"] == {"transport_failed": 1}
    assert trace[-1]["errors"]["lexcheck"] == {"transport_failed": 1}


def test_parallel_workers_overlap(monkeypatch):
    from threading import Barrier
    from types import SimpleNamespace

    from detect.candidates import CandidateBatch
    from detect.client import ModelClient
    from eval.run import evaluate_cases, load_cases

    barrier = Barrier(4, timeout=5)

    def transport(**kwargs):
        barrier.wait()
        return SimpleNamespace(status="completed", output_parsed=CandidateBatch(candidates=()))

    monkeypatch.setenv("LEXCHECK_EVAL_WORKERS", "4")
    report, _ = evaluate_cases(
        load_cases(ROOT / "data/dev")[:4],
        mode="live",
        client=ModelClient(model="test", transport=transport),
    )
    assert all(s.failed_calls == 0 for s in report.systems)
    assert report.systems[1].model_calls == 4


def test_plain_wire_rejections_keep_call_and_denominator_live():
    from types import SimpleNamespace

    from detect.client import ModelClient
    from eval.run import evaluate_cases, load_cases
    from rules.engine import evaluate

    case = next(case for case in load_cases(ROOT / "data/dev") if case[0] == "use-mismatch")
    evaluation = evaluate(case[1])
    finding = next(f for f in evaluation.findings if f.rule_id == "R-02")
    valid = {
        "rule_id": finding.rule_id,
        "record_version_id": finding.record_version_id,
        "clause_quote": finding.clause_quote,
        "evidence": [e.model_dump() for e in finding.evidence],
    }
    invalid = {**valid, "evidence": [{**valid["evidence"][0], "field": "warning"}]}

    def transport(**kwargs):
        assert kwargs["text_format"].__name__ == "WireCandidateBatch"
        return SimpleNamespace(
            status="completed",
            output_parsed=kwargs["text_format"].model_validate({"candidates": [valid, invalid]}),
        )

    report, trace = evaluate_cases(
        (case,), mode="live", client=ModelClient(model="test", transport=transport)
    )
    assert all(s.failed_calls == 0 for s in report.systems)
    assert report.systems[1].evaluated_cases == 1 and report.systems[1].true_positive == 1
    for system in ("plain_chat", "lexcheck"):
        assert trace[0]["rejected_by_system"][system] == {"schema_invalid": 1}
        assert trace[-1]["rejected_by_system"][system] == {"schema_invalid": 1}
