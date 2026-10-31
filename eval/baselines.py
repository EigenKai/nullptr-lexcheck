"""Transparent paired baselines; unavailable predictions are never negatives."""

import json
import unicodedata
from pathlib import Path

from contracts.models import SystemScore
from detect.inputs import model_input
from detect.validator import WARNING

__all__ = ["keyword", "model_input", "score"]
LEXICON = json.loads(Path(__file__).with_name("keyword-lexicon.json").read_text())


def keyword(request, scope):
    targets = [v for v in request.versions if v.id in request.target_version_ids]
    context = [v for v in request.versions if v.id in request.context_version_ids]
    context_uses = {use for v in context for use in v.uses}

    def hit(rule_id, version):
        spec = LEXICON.get(rule_id, {})
        kind = spec.get("kind")
        if kind == "missing_warning":
            return WARNING not in unicodedata.normalize("NFC", version.text)
        if kind == "uses":
            return bool(set(version.uses) - context_uses)
        if kind == "confirmation":
            kinds = {r.id: r.kind for r in request.records}
            return not any(kinds[v.record_id] == "ad_confirmation" for v in context)
        text = version.text.replace(WARNING, "").casefold()
        return any(term.casefold() in text for term in spec.get("phrases", []))

    return {(v.id, r) for v in targets for r in scope if hit(r, v)}


def score(system, rows, calls, failures):
    tp = sum(len(pred & gold) for pred, gold in rows)
    fp = sum(len(pred - gold) for pred, gold in rows)
    fn = sum(len(gold - pred) for pred, gold in rows)
    return SystemScore(
        system=system,
        evaluated_cases=len(rows),
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        false_flags_on_clean=sum(len(pred) for pred, gold in rows if not gold),
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn) if tp + fn else None,
        model_calls=calls,
        failed_calls=failures,
    )
