"""Development measurement with shared input and explicit unmeasured scope."""

import json
import os
from collections import Counter
from pathlib import Path

from contracts.models import CheckRequest, EvaluationReport
from detect.candidates import CandidateBatch
from detect.client import cache_key, configured_client
from detect.inputs import model_input
from detect.service import PROMPT, suggest_with_trace
from detect.validator import validate_findings
from eval.baselines import keyword, score
from rules.engine import evaluate

ROOT = Path(__file__).resolve().parents[1]


def load_cases(directory):
    labels = json.loads((directory / "answers.json").read_text())["cases"]
    paths = sorted((directory / "cases").glob("*.json"))
    return tuple(
        (p.stem, CheckRequest.model_validate_json(p.read_text()), labels[p.stem]) for p in paths
    )


def evaluate_cases(cases, *, phase="dev", mode="off", client=None):
    rows = {name: [] for name in ("keyword", "plain_chat", "lexcheck")}
    calls = Counter()
    failures = Counter()
    trace = []
    active_client = client or configured_client(
        user_id="U-eval", group="manager", acl_hash="synthetic-dev"
    )
    scope_union = set()
    prompt = Path(__file__).with_name("plain-chat-prompt.txt").read_text()
    for name, original, label in cases:
        request = original.model_copy(update={"llm_mode": mode})
        evaluation = evaluate(request)
        scope = set(evaluation.rules_checked)
        scope_union.update(scope)
        gold_all = {tuple(pair) for pair in label["gold"]}
        gold = {(version, rule) for version, rule in gold_all if rule in scope}
        payload = model_input(request, evaluation.rule_snapshots, evaluation.clause_snapshots)
        plain = active_client.generate(
            purpose="plain-chat-v1",
            payload=payload,
            prompt=prompt,
            schema=CandidateBatch,
            mode=mode,
        )
        suggestion = suggest_with_trace(request, evaluation, client=active_client)
        detection = suggestion.result
        validation = validate_findings(
            evaluation.findings + detection.findings,
            request,
            evaluation.rule_snapshots,
            evaluation.clause_snapshots,
        )
        measurable = (
            evaluation.mode == "live" and bool(scope) and evaluation.applicability == "applies"
        )
        if measurable:
            rows["keyword"].append((keyword(request, scope), gold))
            if plain.parsed is not None:
                rows["plain_chat"].append(
                    ({(c.record_version_id, c.rule_id) for c in plain.parsed.candidates}, gold)
                )
            if detection.model_status != "unavailable":
                rows["lexcheck"].append(
                    ({(f.record_version_id, f.rule_id) for f in validation.findings}, gold)
                )
        calls["plain_chat"] += plain.calls
        calls["lexcheck"] += suggestion.calls
        failures["plain_chat"] += int(plain.status == "unavailable")
        failures["lexcheck"] += int(detection.model_status == "unavailable")
        trace.append(
            {
                "case": name,
                "scope": sorted(scope),
                "input_hash": cache_key(payload),
                "prompt_hashes": {"plain_chat": cache_key(prompt), "lexcheck": cache_key(PROMPT)},
                "plain_status": plain.status,
                "lexcheck_status": detection.model_status,
                "rejected": dict(
                    Counter(r.reason for r in validation.rejected)
                    + Counter(dict(suggestion.rejected))
                ),
                "unmeasured_gold_pairs": len(gold_all - gold),
            }
        )
    report = EvaluationReport(
        phase=phase,
        n=len(cases),
        model=active_client.model,
        dataset_sha256=cache_key([(n, r.model_dump(mode="json"), g) for n, r, g in cases]),
        rule_ids=tuple(sorted(scope_union)),
        systems=tuple(score(s, rows[s], calls[s], failures[s]) for s in rows),
        note="Draft labels require owner review. Keyword baseline includes structured uses differences. Scores cover executed rule scope only; unavailable cases excluded. Stability, queue and latency not measured.",
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
