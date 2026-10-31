"""Structural and grounding counts on source inputs; never a legal-accuracy score."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from contracts.models import ClauseVersion
from detect.rulegen import propose_rules


def reference_inputs():
    path = Path(__file__).resolve().parents[1] / "rules/examples/generation/reference.json"
    return tuple(example["input"] for example in json.loads(path.read_text())["examples"])


def evaluate_references(*, client=None):
    inputs = reference_inputs()

    def run(source):
        clause = ClauseVersion(
            id=source["source_id"],
            clause_id=source["source_id"],
            document=source["document"],
            article=source["article"],
            text=source["source_text"],
            source_url=source["source_url"],
            source_sha256=source["source_sha256"],
            retrieved_at=datetime(2026, 10, 31, tzinfo=UTC),
            valid_from=date.min,
            status_note="Reference input only; effective date and legal status unverified.",
        )
        return propose_rules(clause, client=client)

    results = tuple(run(source) for source in inputs)
    return {
        "n": len(inputs),
        "structurally_valid": sum(r.structurally_valid for r in results),
        "grounded": sum(len(r.proposals) for r in results),
        "rejected": sum(r.rejected for r in results),
        "unavailable": sum(r.mode == "unavailable" for r in results),
        "legal_accuracy_measured": False,
    }


def main():
    print(json.dumps(evaluate_references()))


if __name__ == "__main__":
    main()
