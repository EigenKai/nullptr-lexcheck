"""Dispatch the current demo smoke; a requested missing layer fails closed."""

import argparse
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from intake.features import feature_flags
from intake.router import runtime_mode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", default="auto", choices=("auto", "0", "1", "2", "3"))
    args = parser.parse_args()
    is_live = runtime_mode() == "live"
    flags = feature_flags(is_live)
    if args.layer == "auto" and not is_live:
        command = [sys.executable, "-m", "pytest", "-q", "tests/smoke"]
    else:
        layer = (
            args.layer
            if args.layer != "auto"
            else str(
                max(
                    (
                        n
                        for n, enabled in enumerate(
                            (True, flags.layer1, flags.layer2, flags.layer3)
                        )
                        if enabled
                    )
                )
            )
        )
        path = Path("intake/tests/test_smoke_layers.py")
        if not is_live or not path.exists():
            raise SystemExit("Requested live smoke is not implemented yet.")
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(path),
            "-k",
            f"test_layer{layer}_smoke",
        ]
    env = os.environ.copy()
    if args.layer != "auto":
        env.update(
            {f"LEXCHECK_LAYER{i}_ENABLED": "1" if int(args.layer) >= i else "0" for i in (1, 2, 3)}
        )
    with tempfile.TemporaryDirectory(prefix="lexcheck-smoke-") as directory:
        report = Path(directory) / "results.xml"
        result = subprocess.call(command + [f"--junitxml={report}"], env=env)
        if result == 0:
            tree = ET.parse(report)
            cases = tree.findall(".//testcase")
            if not cases or tree.findall(".//skipped"):
                raise SystemExit("Smoke must execute tests without skips.")
        raise SystemExit(result)


if __name__ == "__main__":
    main()
