"""Aggregate pair metrics without document text."""


def pair_metrics(predicted, gold):
    return {
        "true_positive": len(predicted & gold),
        "false_positive": len(predicted - gold),
        "false_negative": len(gold - predicted),
        "false_clean": bool(gold and not predicted),
    }


def per_rule(rows):
    scope = sorted({rule for predicted, gold in rows for _, rule in predicted | gold})
    return {
        rule: pair_metrics(
            {
                (str(i), v)
                for i, (predicted, _) in enumerate(rows)
                for v, r in predicted
                if r == rule
            },
            {(str(i), v) for i, (_, gold) in enumerate(rows) for v, r in gold if r == rule},
        )
        for rule in scope
    }


def stability(traces):
    systems = ("keyword", "plain_chat", "lexcheck")

    def summarize(system):
        predictions = [
            {t["case"]: t["predictions"][system] for t in trace if "predictions" in t}
            for trace in traces
        ]
        names = set.intersection(*(set(run) for run in predictions)) if predictions else set()
        measured = [name for name in names if all(run[name] is not None for run in predictions)]
        stable = sum(
            all(run[name] == predictions[0][name] for run in predictions) for name in measured
        )
        return {
            "measured_cases": len(measured),
            "stable_cases": stable,
            "agreement": stable / len(measured) if measured else None,
        }

    return {system: summarize(system) for system in systems}
