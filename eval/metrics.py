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
        status_key = "plain_status" if system == "plain_chat" else "lexcheck_status"
        statuses = [
            {t["case"]: t.get(status_key) for t in trace if "predictions" in t} for trace in traces
        ]
        measured = [
            name
            for name in names
            if all(run[name] is not None for run in predictions)
            and (system == "keyword" or all(run[name] == "live" for run in statuses))
        ]
        cached = (
            sum(any(run[name] == "cached" for run in statuses) for name in names)
            if system != "keyword"
            else 0
        )
        stable = sum(
            all(run[name] == predictions[0][name] for run in predictions) for name in measured
        )
        return {
            "measured_cases": len(measured),
            "stable_cases": stable,
            "cached_cases": cached,
            "agreement": stable / len(measured) if measured else None,
        }

    return {system: summarize(system) for system in systems}
