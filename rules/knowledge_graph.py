"""Versioned JSON adjacency graph following proposal section 4.1 (layers 1–3)."""

import copy
import hashlib
import json

from contracts.models import Decision, Pattern


def stable_id(prefix: str, payload) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()
    return prefix + "-" + hashlib.sha256(raw).hexdigest()[:24]


class KnowledgeGraph:
    def __init__(self, company_id: str, *, nodes=None, edges=None):
        self.company_id = company_id
        self.nodes = copy.deepcopy(nodes or {})
        self.edges = copy.deepcopy(edges or [])

    def add_node(self, id: str, layer: int, kind: str, payload: dict):
        node = {"layer": layer, "kind": kind, "payload": copy.deepcopy(payload)}
        if id in self.nodes and self.nodes[id] != node:
            raise ValueError("Graph snapshots are immutable; use a new version ID.")
        self.nodes[id] = node

    def link(self, source: str, kind: str, target: str, **metadata):
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("Graph edge references unknown node.")
        edge = {"source": source, "kind": kind, "target": target, **metadata}
        if edge not in self.edges:
            self.edges.append(edge)

    def trace(self, node_id: str) -> list[dict]:
        """Traverse outgoing provenance paths; candidate edges stay labelled."""
        pending, seen, result = [node_id], set(), []
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            for edge in self.edges:
                if edge["source"] == current:
                    result.append(copy.deepcopy(edge))
                    pending.append(edge["target"])
        return result

    def affected_records(self, clause_id: str, *, product_id: str | None = None) -> tuple[str, ...]:
        """Reverse dependency traversal, with a conservative product fallback."""
        pending, seen, affected = [clause_id], set(), set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            node = self.nodes.get(current)
            if node and node["kind"] == "RecordVersion":
                affected.add(current)
            pending.extend(e["source"] for e in self.edges if e["target"] == current)
        if not affected:
            record_ids = {
                id
                for id, n in self.nodes.items()
                if n["kind"] == "Record"
                and (product_id is None or n["payload"]["product_id"] == product_id)
            }
            affected.update(
                id
                for id, n in self.nodes.items()
                if n["kind"] == "RecordVersion" and n["payload"]["record_id"] in record_ids
            )
        return tuple(sorted(affected))

    def as_dict(self):
        return {
            "company_id": self.company_id,
            "nodes": copy.deepcopy(self.nodes),
            "edges": copy.deepcopy(self.edges),
        }

    def record_decision(self, decision: Decision):
        """Append a decision supplied by an already-authorized API caller."""
        request = decision.request
        finding = self.nodes.get(request.finding_id, {})
        check = self.nodes.get(request.check_id, {})
        if finding.get("kind") != "Finding" or request.finding_id not in check.get(
            "payload", {}
        ).get("finding_ids", []):
            raise ValueError("Decision must reference a finding from this company/check snapshot.")
        self.add_node(decision.id, 3, "Decision", decision.model_dump(mode="json"))
        self.link(decision.id, "DECIDES", request.finding_id)
        self.link(decision.id, "FROM_CHECK", request.check_id)

    def record_pattern_candidate(self, pattern: Pattern):
        """Store feedback only; promotion/execution requires separate reviewed guards."""
        if pattern.company_id != self.company_id or pattern.state != "candidate":
            raise ValueError("Only same-company feedback candidates can be stored here.")
        decision = self.nodes.get(pattern.source_decision_id, {})
        if (
            decision.get("kind") != "Decision"
            or decision["payload"]["request"]["action"] != "confirm"
        ):
            raise ValueError("Pattern requires an existing confirmed decision.")
        finding_id = decision["payload"]["request"]["finding_id"]
        finding = self.nodes[finding_id]["payload"]
        if (
            pattern.rule_id != finding["rule_id"]
            or pattern.clause_version_id != finding["clause_version_id"]
            or pattern.rule_version != finding["rule_version"]
        ):
            raise ValueError("Pattern must keep the decision's exact rule/clause versions.")
        if not any(pattern.phrase in (e.get("quote") or "") for e in finding["evidence"]):
            raise ValueError("Pattern phrase must exist in the confirmed evidence.")
        self.add_node(pattern.id, 3, "Pattern", pattern.model_dump(mode="json"))
        self.link(pattern.id, "LEARNED_FROM", pattern.source_decision_id)
        self.link(
            pattern.id, "DERIVED_FROM", pattern.clause_version_id, verification_status="candidate"
        )
