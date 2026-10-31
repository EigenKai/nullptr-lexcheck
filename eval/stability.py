"""Three development runs; cache replay is reported separately from transport calls."""

import json
import os
from collections import Counter

from detect.client import ModelClient
from eval.metrics import stability
from eval.run import ROOT, evaluate_cases, load_cases


def main():
    cases = load_cases(ROOT / "data/dev")
    client = ModelClient(
        cache_dir=None, user_id="U-eval", group="manager", acl_hash="synthetic-dev"
    )
    runs = tuple(
        evaluate_cases(cases, mode=os.getenv("LEXCHECK_LLM_MODE", "off"), client=client)
        for _ in range(3)
    )
    print(
        json.dumps(
            {
                "n": len(cases),
                "repeats": 3,
                "systems": stability([trace for _, trace in runs]),
                "model_calls": sum(s.model_calls for report, _ in runs for s in report.systems),
                "model_statuses": dict(
                    Counter(
                        t[key]
                        for _, trace in runs
                        for t in trace
                        if "case" in t
                        for key in ("plain_status", "lexcheck_status")
                    )
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
