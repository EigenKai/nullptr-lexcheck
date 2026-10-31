"""Bootstrap fixture validation, not performance evaluation."""

import json
from pathlib import Path

from contracts.models import CheckRequest
from intake.fixtures import load_demo


def main():
    bundle = load_demo()
    cases = sorted((Path(__file__).resolve().parents[1] / "data/fixtures/cases").glob("*.json"))
    for path in cases:
        CheckRequest.model_validate_json(path.read_text())
    print(
        json.dumps(
            {
                "phase": "bootstrap",
                "mode": bundle.preview.mode,
                "fixtures_validated": len(cases),
                "measured_cases": 0,
                "metrics": None,
                "note": "No detection performance measured.",
            }
        )
    )


if __name__ == "__main__":
    main()
