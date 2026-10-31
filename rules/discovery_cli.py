"""Local company-law discovery and fast audit. All live calls are opt-in."""

import argparse
import importlib
import json
import os
from pathlib import Path

from contracts.models import CheckRequest
from rules.discovery import Budget, DiscoveryResult, audit, discover


def _path(value: str) -> Path:
    path = Path(value).resolve()
    if any(p.lower() in ("test_final", "nullptr-test-final") for p in path.parts):
        raise argparse.ArgumentTypeError("Held-out evaluation paths are not permitted.")
    return path


def _request(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return CheckRequest.model_validate(data.get("request", data))


def load_local_env(path=Path(".env")):
    """Read only explicit model settings without evaluating shell syntax."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and key.strip() in ("OPENAI_API_KEY", "OPENAI_MODEL"):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if value:
                os.environ.setdefault(key.strip(), value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--input", required=True, type=_path)
    ingest.add_argument("--description", required=True)
    ingest.add_argument("--output", required=True, type=_path)
    ingest.add_argument("--live", action="store_true")
    ingest.add_argument("--model")
    ingest.add_argument(
        "--transport",
        help="Optional explicit module:factory, e.g. detect.client:discovery_transport",
    )
    ingest.add_argument("--max-seconds", type=float, default=180)
    ingest.add_argument("--max-sources", type=int, default=8)
    ingest.add_argument("--max-rounds", type=int, default=6)
    ingest.add_argument(
        "--source-url",
        action="append",
        default=[],
        help="Optional user-provided official law URL; never a sample rule.",
    )
    check = commands.add_parser("audit")
    check.add_argument("--input", required=True, type=_path)
    check.add_argument("--graph", required=True, type=_path)
    check.add_argument("--output", required=True, type=_path)
    args = parser.parse_args()
    request = _request(args.input)
    if args.command == "ingest":
        if not args.live:
            parser.error(
                "Pass --live to authorize model calls and official-source retrieval. No sample fallback is used."
            )
        load_local_env()
        if args.transport:
            module, factory = args.transport.split(":", 1)
            transport = getattr(importlib.import_module(module), factory)()
        else:
            from detect.client import DiscoveryTransport

            transport = DiscoveryTransport(model=args.model, cache_dir=Path("cache/discovery-api"))
        result = discover(
            request,
            args.description,
            transport,
            budget=Budget(
                max_seconds=args.max_seconds,
                max_sources=args.max_sources,
                max_rounds=args.max_rounds,
            ),
            seed_urls=args.source_url,
        )
        result.save(args.output)
        print(
            json.dumps(
                {
                    "graph": str(args.output),
                    "rules_generated": len(result.rules),
                    "stop_reason": result.stop_reason,
                    "missing_topics": result.missing_topics,
                    "errors": result.errors,
                    "provenance": result.provenance,
                },
                ensure_ascii=False,
            )
        )
        return 0 if result.rules else 2
    result = DiscoveryResult.load(args.graph, company_id=request.profile.company_id)
    report = audit(result, request)
    graph_path = args.output.with_suffix(".graph.json")
    result.save(graph_path)
    report["graph_snapshot"] = str(graph_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(args.output),
                "findings": len(report["findings"]),
                "model_calls_during_audit": report.get("model_calls_during_audit", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
