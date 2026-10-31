"""Narrow medicinal-language review and selected registration-document checks."""

import re
from datetime import date

from contracts.models import Evidence
from rules.endorsement import _mapped_text

MEDICINAL_TERMS = ("chữa khỏi", "đặc trị", "điều trị", "thay thế thuốc chữa bệnh")
_MEDICINAL = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in MEDICINAL_TERMS) + r")\b")
_NEGATIVE = re.compile(r"\b(?:không|chưa)(?:\s+(?:có|tác dụng|khả năng|thể|được|dùng để)){0,4}\s*$")
AUTHORITY_CUTOFF = date(2026, 7, 1)


def medicinal(version):
    text, locations = _mapped_text(version.text)
    evidence = []
    for match in _MEDICINAL.finditer(text):
        start, end = match.span()
        boundary = max(text.rfind(mark, 0, start) for mark in ".!?;,\n") + 1
        prefix = text[boundary:start]
        if _NEGATIVE.search(prefix) or (match.group() == "điều trị" and prefix.endswith("hỗ trợ ")):
            continue
        raw_start, raw_end = locations[start][0], locations[end - 1][1]
        evidence.append(
            Evidence(
                record_version_id=version.id,
                kind="span",
                quote=version.text[raw_start:raw_end],
                start=raw_start,
                end=raw_end,
            )
        )
    return tuple(evidence), True


def connected(version, request, records, selected, kind):
    linked = {v.record_id for v in request.versions if v.id in version.reference_ids}
    return tuple(
        v
        for v in selected
        if v.id in request.context_version_ids
        and v.record_id in linked
        and records[v.record_id].kind == kind
        and records[v.record_id].product_id == records[version.record_id].product_id
    )


def attachment(version, request, records, selected, kind, field):
    if connected(version, request, records, selected, kind):
        return (), True
    return (Evidence(record_version_id=version.id, kind="missing_field", field=field),), True


def authority(version, request, records, selected):
    candidates = (
        (version,)
        if records[version.record_id].kind == "ad_confirmation"
        else connected(version, request, records, selected, "ad_confirmation")
    )
    if len(candidates) != 1:
        return (), False
    source = candidates[0]
    if source.confirmation_date is None:
        # Current shared validator considers date presence across all selected
        # records; do not emit a rejection-prone flag for an ambiguous scope.
        if any(v.confirmation_date is not None for v in selected):
            return (), False
        return (
            Evidence(record_version_id=source.id, kind="missing_field", field="confirmation_date"),
        ), True
    if source.confirmation_date < AUTHORITY_CUTOFF:
        return (), True
    if source.issuing_authority == "provincial_chair":
        return (), True
    if source.issuing_authority == "unknown":
        if any(v.issuing_authority != "unknown" for v in selected):
            return (), False
        return (
            Evidence(record_version_id=source.id, kind="missing_field", field="issuing_authority"),
        ), True
    text, locations = _mapped_text(source.text)
    match = re.search(r"\b(?:cục an toàn thực phẩm|bộ y tế)\b", text)
    if match is None:
        return (), False
    start, end = locations[match.start()][0], locations[match.end() - 1][1]
    return (
        Evidence(
            record_version_id=source.id,
            kind="span",
            quote=source.text[start:end],
            start=start,
            end=end,
        ),
    ), True
