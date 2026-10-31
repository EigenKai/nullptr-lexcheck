"""Closed text dictionary for medical advertising references, with raw offsets."""

import re
import unicodedata

MEDICAL = (
    "bác sĩ",
    "bác sỹ",
    "dược sĩ",
    "dược sỹ",
    "nhân viên y tế",
    "cơ sở y tế",
    "đơn vị y tế",
    "bệnh viện",
    "phòng khám",
)
ENDORSEMENTS = (
    "khuyên dùng",
    "khuyên sử dụng",
    "khuyên chọn",
    "khuyến nghị",
    "khuyến cáo dùng",
    "giới thiệu",
    "bảo chứng",
    "chứng nhận",
    "tin dùng",
)
ARTIFACTS = ("hình ảnh", "thiết bị", "trang phục", "tên", "thư tín", "bài viết")


def _alternatives(words):
    return "(?:" + "|".join(re.escape(word) for word in words) + ")"


_medical = _alternatives(MEDICAL)
_endorse = _alternatives(ENDORSEMENTS)
_artifact = _alternatives(ARTIFACTS)
_CANDIDATES = tuple(
    re.compile(r"(?=(\b" + expression + r"\b))")
    for expression in (
        _medical + r"\b[^.!?;]{0,80}?\b" + _endorse,
        _endorse + r"\b[^.!?;]{0,40}?\b(?:bởi|của)\s+" + _medical,
        _artifact + r"\s+(?:của\s+)?" + _medical,
        r"thư cảm ơn\s+(?:của|từ)\s+(?:người bệnh|bệnh nhân)",
    )
)
_NEGATIVE = re.compile(r"\b(?:không|chưa|cấm|tránh)\b")
_NEGATIVE_BEFORE = re.compile(
    r"\b(?:không|chưa|cấm|tránh)"
    r"(?:\s+(?:được|nên|hề|có|dùng|sử dụng|từng|phép|bất kỳ|bất cứ)){0,5}\s*$"
)
_ADVICE = re.compile(r"(?:hỏi|tham khảo|xin)\s+(?:ý kiến\s+)?(?:của\s+)?$")
_POLICY = re.compile(r"^(?:theo quy định[, :]*)?(?:không|cấm|nghiêm cấm)\s+(?:sử dụng|dùng)\b")


def _mapped_text(raw):
    """Compose/casefold matching text while retaining every original code point."""
    text, locations = [], []
    cursor = 0
    while cursor < len(raw):
        end = cursor + 1
        while end < len(raw) and unicodedata.combining(raw[end]):
            end += 1
        for char in unicodedata.normalize("NFC", raw[cursor:end]).casefold():
            if char.isspace():
                if text and text[-1] == " ":
                    locations[-1] = (locations[-1][0], end)
                    continue
                char = " "
            text.append(char)
            locations.append((cursor, end))
        cursor = end
    return "".join(text), locations


def spans(raw):
    """Return exact raw spans; a match is a review item, never a legal verdict.

    Only explicit dictionary phrases in text/captions are covered. No image
    content, unnamed clinician identity, irony or implied endorsement is inferred.
    """
    text, locations = _mapped_text(raw)
    found = set()
    for pattern in _CANDIDATES:
        for match in pattern.finditer(text):
            start, end = match.span(1)
            sentence_start = max(text.rfind(mark, 0, start) for mark in ".!?;") + 1
            prefix = text[sentence_start:start]
            local_prefix = prefix.rsplit(",", 1)[-1]
            if (
                _POLICY.search(text[sentence_start:].lstrip())
                or _NEGATIVE_BEFORE.search(local_prefix)
                or _NEGATIVE.search(text[start:end])
                or _ADVICE.search(local_prefix)
            ):
                continue
            found.add((locations[start][0], locations[end - 1][1]))
    # Prefer the containing phrase when two dictionary mechanisms overlap.
    return tuple(
        (start, end)
        for start, end in sorted(found)
        if not any(a <= start and end <= b and (a, b) != (start, end) for a, b in found)
    )
