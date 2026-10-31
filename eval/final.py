"""Single-use aggregate evaluation. Human-operated; never writes case data to the repository."""

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from contracts.models import CheckRequest
from detect.client import ModelClient, cache_key
from detect.service import PROMPT
from eval.run import ROOT, evaluate_cases

MAX_INPUT_BYTES = 20_000_000


def _write_exclusive(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(data, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())


def _read(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_INPUT_BYTES:
            raise ValueError("invalid_input")
        return handle.read(MAX_INPUT_BYTES + 1)


def _capture(directory):
    paths = [directory / "answers.json", *sorted((directory / "cases").glob("*.json"))]
    if len(paths) < 2 or (directory / "cases").is_symlink():
        raise PreflightError("empty_or_linked_dataset")
    return tuple((p, _read(p)) for p in paths)


def _manifest(inputs, mode):
    return {
        "input_hashes": [hashlib.sha256(content).hexdigest() for _, content in inputs],
        "dataset_sha256": cache_key([hashlib.sha256(c).hexdigest() for _, c in inputs]),
        "git_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "flags": {
            key: os.getenv(key, "0")
            for key in (
                "LEXCHECK_LAYER1_ENABLED",
                "LEXCHECK_LAYER2_ENABLED",
                "LEXCHECK_LAYER3_ENABLED",
            )
        },
        "mode": mode,
        "model": os.getenv("OPENAI_MODEL"),
        "rule_hash": cache_key(
            [
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                for path in ("rules/catalog.json", "rules/clauses.json")
            ]
        ),
        "dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "prompt_hashes": {
            "lexcheck": cache_key(PROMPT),
            **{
                system: cache_key((ROOT / "eval/plain-chat-prompt.txt").read_text())
                for system in ("plain_chat", "plain_chat_web", "retrieval")
            },
        },
    }


def _parse(inputs):
    labels = json.loads(inputs[0][1])["cases"]
    if set(labels) != {path.stem for path, _ in inputs[1:]}:
        raise PreflightError("label_mismatch")
    cases = tuple(
        (p.stem, CheckRequest.model_validate_json(content), labels[p.stem])
        for p, content in inputs[1:]
    )
    for _, request, label in cases:
        if not isinstance(label["gold"], list) or any(
            not isinstance(pair, list)
            or len(pair) != 2
            or pair[0] not in request.target_version_ids
            or not isinstance(pair[1], str)
            for pair in label["gold"]
        ):
            raise PreflightError("invalid_labels")
    return cases


class PreflightError(ValueError):
    pass


def run(directory, *, mode=None, check_only=False):
    directory = directory.resolve()
    if directory.is_relative_to(ROOT):
        return {"error": "directory_inside_repository"}, 2
    if not directory.is_dir():
        return {"error": "directory_missing"}, 2
    if (directory / ".lexcheck-run.json").exists():
        return {"error": "already_run"}, 2
    if mode not in ("off", "live"):
        return {"error": "mode_required"}, 2
    if mode == "live" and not (os.getenv("OPENAI_MODEL") and os.getenv("OPENAI_API_KEY")):
        return {"error": "live_configuration_missing"}, 2
    try:
        inputs = _capture(directory)
        cases = _parse(inputs)
        manifest = _manifest(inputs, mode)
    except PreflightError as error:
        return {"error": str(error)}, 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {"error": "invalid_dataset"}, 2
    if check_only:
        return {
            "mode": mode,
            "model": manifest["model"],
            "n": len(cases),
            "git_sha": manifest["git_sha"],
            "dirty": manifest["dirty"],
            "dataset_sha256": manifest["dataset_sha256"],
        }, 0
    if mode == "live" and manifest["dirty"]:
        return {"error": "dirty_tree"}, 2
    try:
        _write_exclusive(directory / ".lexcheck-run.json", {"state": "consumed"})
    except FileExistsError:
        return {"error": "already_run"}, 2
    except OSError:
        return {"error": "marker_failed"}, 2
    try:
        _write_exclusive(directory / "final-manifest.json", manifest)
        # No cache persistence; all input is the captured, hashed bytes above.
        report, trace = evaluate_cases(cases, phase="held_out", mode=mode, client=ModelClient())
        output = report.model_copy(
            update={
                "git_sha": manifest["git_sha"],
                "dataset_sha256": manifest["dataset_sha256"],
                "note": "Single-use measurement; only executed scope counted. Unavailable cases excluded. B, B+ and R score raw model candidates; LexCheck scores validated findings.",
            }
        ).model_dump(mode="json")
        _write_exclusive(directory / "final-diagnostics.json", trace[-1])
        _write_exclusive(directory / "final-results.json", output)
        return output, 0
    except Exception:  # noqa: BLE001 - fixed error code, no input-bearing diagnostics
        return {"error": "run_failed"}, 2


def main(argv=None):
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--mode", choices=("off", "live"), default=os.getenv("LEXCHECK_LLM_MODE"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    output, code = run(args.directory, mode=args.mode, check_only=args.check)
    print(json.dumps(output, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
