"""Development measurement with shared input and explicit unmeasured scope."""

import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter

from contracts.models import CheckRequest, EvaluationReport
from detect.candidates import WireCandidateBatch, validate_candidates
from detect.client import cache_key, configured_client
from detect.inputs import model_input
from detect.service import PROMPT, suggest_with_trace
from detect.validator import validate_findings
from detect.versions import assess_basis
from eval.baselines import keyword, score
from eval.metrics import per_rule
from eval.retrieval import retrieval_payload
from rules.engine import evaluate

ROOT = Path(__file__).resolve().parents[1]


def load_cases(directory):
    labels = json.loads((directory / "answers.json").read_text())["cases"]
    paths = sorted((directory / "cases").glob("*.json"))
    return tuple(
        (p.stem, CheckRequest.model_validate_json(p.read_text()), labels[p.stem]) for p in paths
    )


SYSTEMS = ("keyword", "plain_chat", "plain_chat_web", "retrieval", "lexcheck")


def eval_workers():
    try:
        value = int(os.getenv("LEXCHECK_EVAL_WORKERS", "6"))
    except ValueError:
        return 6
    return value if 1 <= value <= 64 else 6


def _evaluate_case(case, *, mode, active_client, prompt):
    name, original, label = case
    rows = {system: [] for system in SYSTEMS}
    calls, failures = Counter(), Counter()
    latencies = {system: [] for system in SYSTEMS}
    request = original.model_copy(update={"llm_mode": mode})
    evaluation = evaluate(request)
    scope = set(evaluation.rules_checked)
    gold_all = {tuple(pair) for pair in label["gold"]}
    gold = {(version, rule) for version, rule in gold_all if rule in scope}
    payload = model_input(request, evaluation.rule_snapshots, evaluation.clause_snapshots)
    outputs, batches, rejections = {}, {}, {}
    for system, purpose, model_payload, tools in (
        ("plain_chat", "plain-chat-v1", payload, ()),
        ("plain_chat_web", "plain-chat-web-v1", payload, ({"type": "web_search"},)),
        ("retrieval", "retrieval-v1", retrieval_payload(payload), ()),
    ):
        started = perf_counter()
        output = active_client.generate(
            purpose=purpose,
            payload=model_payload,
            prompt=prompt,
            schema=WireCandidateBatch,
            mode=mode,
            **({"tools": tools} if tools else {}),
        )
        outputs[system] = output
        batch, invalid = (
            validate_candidates(output.parsed) if output.parsed is not None else (None, 0)
        )
        batches[system] = batch
        rejections[system] = {"schema_invalid": invalid} if invalid else {}
        if output.calls:
            latencies[system].append((perf_counter() - started) * 1000)
        calls[system] = output.calls
        failures[system] = int(output.status == "unavailable")
    started = perf_counter()
    suggestion = suggest_with_trace(request, evaluation, client=active_client)
    if suggestion.calls:
        latencies["lexcheck"].append((perf_counter() - started) * 1000)
    detection = suggestion.result
    validation = validate_findings(
        evaluation.findings + detection.findings,
        request,
        evaluation.rule_snapshots,
        evaluation.clause_snapshots,
    )
    basis = assess_basis(
        request,
        evaluation.rule_snapshots,
        evaluation.clause_snapshots,
        rules_checked=evaluation.rules_checked,
    )
    measurable = (
        evaluation.mode == "live"
        and bool(scope)
        and evaluation.applicability == "applies"
        and basis.status == "ready"
    )
    predictions = {system: None for system in SYSTEMS}
    if measurable:
        predictions["keyword"] = sorted(keyword(request, scope))
        for system, output in outputs.items():
            if output.parsed is not None:
                predictions[system] = sorted(
                    {(c.record_version_id, c.rule_id) for c in batches[system].candidates}
                )
        if detection.model_status != "unavailable":
            predictions["lexcheck"] = sorted(
                {(f.record_version_id, f.rule_id) for f in validation.findings}
            )
    for system, predicted in predictions.items():
        if predicted is not None:
            rows[system].append((set(predicted), gold))
    calls["lexcheck"] += suggestion.calls
    failures["lexcheck"] += int(detection.model_status == "unavailable")
    trace = {
        "case": name,
        "predictions": predictions,
        "basis_status": basis.status,
        "scope": sorted(scope),
        "input_hash": cache_key(payload),
        "prompt_hashes": {
            **{system: cache_key(prompt) for system in outputs},
            "lexcheck": cache_key(PROMPT),
        },
        "plain_status": outputs["plain_chat"].status,
        "plain_chat_web_status": outputs["plain_chat_web"].status,
        "retrieval_status": outputs["retrieval"].status,
        "lexcheck_status": detection.model_status,
        "rejected": dict(
            Counter(r.reason for r in validation.rejected) + Counter(dict(suggestion.rejected))
        ),
        "errors": {
            **{system: output.error for system, output in outputs.items()},
            "lexcheck": suggestion.error,
        },
        "rejected_by_system": {**rejections, "lexcheck": dict(suggestion.rejected)},
        "unmeasured_gold_pairs": len(gold_all - gold),
    }
    return rows, calls, failures, latencies, trace, scope


def evaluate_cases(cases, *, phase="dev", mode="off", client=None):
    cases = tuple(sorted(cases, key=lambda case: case[0]))
    rows = {system: [] for system in SYSTEMS}
    calls, failures = Counter(), Counter()
    latencies = {system: [] for system in SYSTEMS}
    trace, scope_union = [], set()
    active_client = client or configured_client(
        user_id="U-eval", group="manager", acl_hash="synthetic-dev"
    )
    prompt = Path(__file__).with_name("plain-chat-prompt.txt").read_text()

    def run_case(case):
        return _evaluate_case(case, mode=mode, active_client=active_client, prompt=prompt)

    with ThreadPoolExecutor(max_workers=eval_workers()) as executor:
        for case_rows, case_calls, case_failures, case_latencies, entry, scope in executor.map(
            run_case, cases
        ):
            for system in SYSTEMS:
                rows[system].extend(case_rows[system])
                latencies[system].extend(case_latencies[system])
            calls.update(case_calls)
            failures.update(case_failures)
            trace.append(entry)
            scope_union.update(scope)
    report = EvaluationReport(
        phase=phase,
        n=len(cases),
        model=active_client.model,
        dataset_sha256=cache_key([(n, r.model_dump(mode="json"), g) for n, r, g in cases]),
        rule_ids=tuple(sorted(scope_union)),
        systems=tuple(
            score(s, rows[s], calls[s], failures[s]).model_copy(
                update={
                    "latency_ms": sum(latencies[s]) / len(latencies[s]) if latencies[s] else None
                }
            )
            for s in rows
        ),
        note="B, B+ and R score raw model candidates; LexCheck scores validated findings. Draft labels require owner review. Keyword baseline includes structured uses differences. Scores cover executed rule scope only; unavailable cases excluded. Latency measures logical transport calls when available; queue metrics not measured.",
    )
    trace.append(
        {
            "errors": {
                s: dict(Counter(t["errors"].get(s) for t in trace if t["errors"].get(s)))
                for s in SYSTEMS
            },
            "rejected_by_system": {
                system: dict(
                    sum(
                        (Counter(t["rejected_by_system"].get(system, {})) for t in trace), Counter()
                    )
                )
                for system in SYSTEMS
            },
            "per_rule": {s: per_rule(rows[s]) for s in rows},
            "false_clean": {
                s: sum(bool(gold and not predicted) for predicted, gold in rows[s]) for s in rows
            },
        }
    )
    return report, trace


def main():
    report, trace = evaluate_cases(
        load_cases(ROOT / "data/dev"), mode=os.getenv("LEXCHECK_LLM_MODE", "off")
    )
    output = ROOT / "eval/results"
    output.mkdir(exist_ok=True)
    (output / "latest.json").write_text(report.model_dump_json(indent=2) + "\n")
    (output / "trace.json").write_text(json.dumps(trace, indent=2) + "\n")
    print(report.model_dump_json())


if __name__ == "__main__":
    main()
