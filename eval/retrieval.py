"""Deterministic lexical retrieval over source text only, without graph or labels."""

import json
import math
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_K = 3


def tokens(text):
    return frozenset(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


def passages():
    clauses = json.loads((ROOT / "rules/clauses.json").read_text())
    examples = json.loads((ROOT / "rules/examples/generation/reference.json").read_text())[
        "examples"
    ]
    return tuple({"id": clause["id"], "text": clause["text"]} for clause in clauses) + tuple(
        {"id": example["input"]["source_id"], "text": example["input"]["source_text"]}
        for example in examples
    )


def retrieve(query):
    """IDF-weighted token overlap; ties by source ID, including zero-overlap queries."""
    corpus = passages()
    document_tokens = tuple(tokens(passage["text"]) for passage in corpus)
    query_tokens = tokens(query)
    weights = {
        token: math.log(1 + len(corpus) / (1 + sum(token in terms for terms in document_tokens)))
        for token in query_tokens
    }
    scores = tuple(
        sum(weights[token] for token in sorted(query_tokens & terms)) for terms in document_tokens
    )
    ranked = sorted(zip(corpus, scores), key=lambda pair: (-pair[1], pair[0]["id"]))
    return tuple(passage for passage, _ in ranked[:TOP_K])


def retrieval_payload(payload):
    request = payload["request"]
    query = "\n".join(
        version["text"]
        for version in request["versions"]
        if version["id"] in request["target_version_ids"]
    )
    return {**payload, "clauses": list(retrieve(query))}
