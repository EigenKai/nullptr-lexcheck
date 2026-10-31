"""Synthetic medical-endorsement checks; no OCR or image recognition is implied."""

import unicodedata

import pytest

from detect.validator import validate_findings
from rules.engine import evaluate
from rules.tests.test_engine import case, change_version
from rules.tests.test_sources import catalog, clauses


def checked(text):
    request = change_version(case(), text=text)
    rule = next(r for r in catalog() if r.id == "R-04")
    clause = clauses()[rule.clause_version_id]
    result = evaluate(request, rules=(rule,), clauses=(clause,))
    validation = validate_findings(
        result.findings, request, result.rule_snapshots, result.clause_snapshots
    )
    assert validation.rejected == ()
    assert validation.findings == result.findings
    return result


@pytest.mark.parametrize(
    "text",
    [
        "Sản phẩm được bác sĩ An khuyên dùng mỗi ngày.",
        "Bệnh viện Bình Minh giới thiệu sản phẩm này.",
        "Hình ảnh bác sỹ An trên ma két quảng cáo sản phẩm.",
        "Tên cơ sở y tế Bình Minh được đưa lên quảng cáo.",
        "Thư cảm ơn của người bệnh về sản phẩm.",
        "Bài viết của dược sỹ An giới thiệu sản phẩm.",
        "Sản phẩm không đường, bác sĩ An khuyên dùng mỗi ngày.",
    ],
)
def test_positive_cases(text):
    result = checked(text)
    assert result.rules_checked == ("R-04",)
    assert result.findings
    assert all(f.status == "needs_review" and f.source == "rule" for f in result.findings)
    for finding in result.findings:
        evidence = finding.evidence[0]
        assert text[evidence.start : evidence.end] == evidence.quote


@pytest.mark.parametrize(
    "text",
    [
        "Hỏi ý kiến bác sĩ trước khi dùng.",
        "Hãy tham khảo ý kiến dược sỹ trước khi sử dụng sản phẩm.",
        "Không sử dụng hình ảnh bác sĩ để quảng cáo thực phẩm.",
        "Không có bác sĩ nào khuyên dùng sản phẩm này.",
        "Sản phẩm chưa được bệnh viện khuyến nghị.",
        "Không dùng thư cảm ơn của người bệnh để quảng cáo.",
        "Tài liệu được gửi cho cơ sở y tế để hỏi thủ tục.",
    ],
)
def test_negative_cases(text):
    result = checked(text)
    assert result.rules_checked == ("R-04",)
    assert result.findings == ()


def test_raw_offsets_preserve_decomposed_unicode_and_emoji():
    text = "🧪  " + unicodedata.normalize("NFD", "BÁC SĨ An khuyên dùng") + "."
    result = checked(text)
    evidence = result.findings[0].evidence[0]
    assert evidence.start == 3
    assert text[evidence.start : evidence.end] == evidence.quote
    assert "A\u0301" in evidence.quote


def test_safety_advice_does_not_hide_later_endorsement():
    text = "Hỏi ý kiến bác sĩ trước khi dùng; bác sĩ An khuyên dùng sản phẩm."
    result = checked(text)
    assert len(result.findings) == 1
    assert result.findings[0].evidence[0].start == text.index("bác sĩ An")


def test_catalog_basis_is_exact_subquote_of_previously_confirmed_cv02():
    basis = clauses()
    clause = basis["CV-04-v1"]
    assert clause.text.startswith("Không sử dụng hình ảnh")
    assert clause.text.endswith("để quảng cáo thực phẩm.")
    assert clause.text in basis["CV-02-v1"].text
    assert clause.verified_by == basis["CV-02-v1"].verified_by == "Dung"
    assert clause.verified_at == basis["CV-02-v1"].verified_at
    assert clause.source_sha256 == basis["CV-02-v1"].source_sha256


def test_default_engine_counts_four_rules_exactly_and_is_immutable():
    request = case("endorsement")
    original = request.model_dump_json()
    result = evaluate(request)
    assert result.rules_checked == ("R-01", "R-02", "R-03", "R-04")
    assert any(f.rule_id == "R-04" for f in result.findings)
    validation = validate_findings(
        result.findings, request, result.rule_snapshots, result.clause_snapshots
    )
    assert validation.rejected == ()
    assert request.model_dump_json() == original
    assert evaluate(request) == result
