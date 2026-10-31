"""Bounded housing research into incomplete proposals, outside the active rule pack."""

import re
import time
from dataclasses import asdict
from datetime import UTC, datetime

from contracts.models import ClauseVersion
from rules.discovery import Budget, _article_matches, _document_key, _page_selection, _unresolved
from rules.discovery_models import ResearchPlan, SearchResult
from rules.knowledge_graph import KnowledgeGraph, stable_id
from rules.legal_sources import OFFICIAL_DOMAINS, fetch_source, validate_url
from rules.workspace_models import HousingExtraction


def research(workspace, transport, *, fetcher=fetch_source, budget=None, progress=None):
    budget = budget or Budget(max_sources=5, max_rounds=4, max_seconds=300)
    emit = progress or (lambda stage, message: None)
    started = time.monotonic()
    deadline = started + budget.max_seconds
    graph = KnowledgeGraph(workspace["id"])
    graph.add_node(
        workspace["id"],
        3,
        "Company",
        {"name": workspace["name"], "domain": "rental_housing", "legal_name_confirmed": False},
    )
    manifest = workspace["manifest"]
    workbook_id = stable_id("WORKBOOK", [workspace["id"], manifest["sha256"]])
    graph.add_node(workbook_id, 3, "WorkbookSnapshot", manifest)
    graph.link(workbook_id, "BELONGS_TO", workspace["id"])
    for sheet in manifest["sheets"]:
        sheet_id = stable_id("SHEET", [workbook_id, sheet["index"]])
        graph.add_node(sheet_id, 3, "SheetSnapshot", sheet)
        graph.link(workbook_id, "CONTAINS", sheet_id)
    context = {
        "workspace_id": workspace["id"],
        "domain": "rental_housing",
        "business_description": workspace["description"]
        or "Hoạt động cho thuê và quản lý nhà trọ tại Việt Nam; chưa xác nhận hình thức pháp lý, địa phương, quy mô, doanh thu.",
        "observed_workbook_categories": manifest["signals"],
        "unknown_facts": manifest["unknown_facts"],
        "review_date": workspace["review_date"],
        "scope_note": "Sheet presence is only an inventory signal, never proof a legal procedure was or was not completed. This is a private example, not a synthetic claim about actual records.",
    }
    gaps, proposals, calls, covered, seen = [], {}, [], set(), set()
    attempts, stalls, stop = 0, 0, "round_budget"

    def complete(stage, data, model, web_search=False):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Research time budget exhausted.")
        calls.append(stage)
        return model.model_validate(
            transport.complete(
                stage,
                {**context, **data},
                model.model_json_schema(),
                timeout_s=remaining,
                web_search=web_search,
            )
        )

    emit(
        "plan", "Đang xác định các nhóm nghĩa vụ từ cấu trúc Excel, không gửi ô dữ liệu người thuê."
    )
    try:
        plan = complete(
            "plan",
            {
                "instruction": "Identify at most 5 rental-housing obligation topics from workbook categories; include applicable thresholds, missing business facts and legal updates. Do not assume locality or scale."
            },
            ResearchPlan,
        )
        if len({t.id for t in plan.topics}) != len(plan.topics):
            raise ValueError("Duplicate topic IDs.")
    except (ValueError, RuntimeError, TimeoutError):
        return _result(
            graph,
            {},
            (),
            (),
            "provider_unavailable",
            ["research_plan_unavailable"],
            calls,
            transport,
            started,
            budget,
            0,
        )
    for round_index in range(budget.max_rounds):
        if time.monotonic() >= deadline:
            stop = "time_budget"
            break
        if attempts >= budget.max_sources:
            stop = "source_budget"
            break
        uncovered = [t for t in plan.topics if t.id not in covered]
        if not uncovered and not _unresolved(graph):
            stop = "topic_coverage"
            break
        emit(
            "search",
            f"Lượt {round_index + 1}: tìm nguồn chính thức và văn bản sửa đổi; đã đọc {attempts} nguồn.",
        )
        try:
            links = complete(
                "search",
                {
                    "topics": [t.model_dump(mode="json") for t in uncovered or plan.topics],
                    "already_seen": sorted(seen),
                    "unresolved_documents": _unresolved(graph)[:8],
                    "retrieval_gaps": gaps[-6:],
                    "official_domains": OFFICIAL_DOMAINS,
                },
                SearchResult,
                True,
            )
        except (ValueError, RuntimeError, TimeoutError):
            gaps.append("search_unavailable:could not confirm updates from this source")
            stop = "provider_unavailable"
            break
        novelty = 0
        for link in links.sources:
            if attempts >= budget.max_sources:
                stop = "source_budget"
                break
            if len(proposals) >= budget.max_rules:
                stop = "rule_budget"
                break
            try:
                url = validate_url(link.url)
                if url in seen:
                    continue
                seen.add(url)
                novelty += 1
                attempts += 1
                if time.monotonic() >= deadline:
                    stop = "time_budget"
                    break
                emit("download", f"Đang tải nguồn {attempts}/{budget.max_sources}: {url}")
                source = (
                    fetcher(url, timeout_s=min(90, max(1, deadline - time.monotonic())))
                    if fetcher is fetch_source
                    else fetcher(url)
                )
                if source.id in graph.nodes:
                    continue
                gaps.extend(source.id + ":" + warning for warning in source.warnings)
                graph.add_node(
                    source.id,
                    1,
                    "LegalDoc",
                    {
                        "url": source.url,
                        "sha256": source.sha256,
                        "title": source.title,
                        "pages": list(source.pages),
                        "extraction_method": source.extraction_method,
                        "verification_status": "to_be_verified",
                    },
                )
                selected = _page_selection(source, plan.topics)
                if not selected:
                    gaps.append(source.id + ":requires_ocr")
                    continue
                emit(
                    "extract",
                    f"Đang đọc {len(selected)}/{len(source.pages)} trang để sinh rule đề xuất; nguồn chưa được người duyệt xác minh.",
                )
                extraction = complete(
                    "extract",
                    {
                        "source_url": source.url,
                        "pages": selected,
                        "omitted_pages": len(source.pages) - len(selected),
                        "topics": [t.model_dump(mode="json") for t in plan.topics],
                        "extraction_mode": "housing_obligation_proposals",
                        "instruction": "Return at most 8 distinct operator obligations. Exact quotes only. Dates need an exact date_quote/date_page. Keep unknown dates null. Include applicability thresholds and missing facts; do not infer local authority, floor/room counts, completion or absence of procedures from a sheet. No advertising/TPBVSK categories.",
                    },
                    HousingExtraction,
                )
                if (
                    extraction.document_number
                    and _document_key(extraction.document_number)
                    not in re.sub(r"\s+", "", "\n".join(source.pages)).casefold()
                ):
                    gaps.append(source.id + ":document_number_not_grounded")
                    extraction = extraction.model_copy(update={"document_number": ""})
                if len(selected) < len(source.pages):
                    gaps.append(source.id + ":pages_omitted_by_context_budget")
                for node_id, node in list(graph.nodes.items()):
                    if (
                        node["kind"] == "UnresolvedDocument"
                        and extraction.document_number
                        and _document_key(node["payload"]["title"])
                        == _document_key(extraction.document_number)
                        and extraction.document_number.casefold()
                        in "\n".join(source.pages).casefold()
                    ):
                        graph.link(
                            node_id, "RESOLVED_AS", source.id, verification_status="candidate"
                        )
                for proposal in extraction.proposals:
                    if len(proposals) >= budget.max_rules:
                        stop = "rule_budget"
                        break
                    if proposal.actor != "operator":
                        gaps.append(source.id + ":not_operator_obligation")
                        continue
                    if proposal.topic_id not in {t.id for t in plan.topics}:
                        gaps.append(source.id + ":unknown_topic")
                        continue
                    page = next((p["text"] for p in selected if p["page"] == proposal.page), "")
                    start = page.find(proposal.quote)
                    if start < 0 or not _article_matches(source, proposal, start):
                        gaps.append(source.id + ":quote_or_article_mismatch")
                        continue
                    date_page = next(
                        (p["text"] for p in selected if p["page"] == proposal.date_page), ""
                    )
                    date_grounded = bool(proposal.date_quote and proposal.date_quote in date_page)
                    valid_from = (
                        proposal.valid_from
                        if date_grounded and _date_appears(proposal.valid_from, proposal.date_quote)
                        else None
                    )
                    valid_to = (
                        proposal.valid_to
                        if date_grounded and _date_appears(proposal.valid_to, proposal.date_quote)
                        else None
                    )
                    if not valid_from:
                        gaps.append(source.id + ":effective_date_missing")
                    if valid_from and valid_to and valid_to <= valid_from:
                        gaps.append(source.id + ":invalid_date_interval")
                        continue
                    article_id = stable_id("ART", [source.id, proposal.article])
                    clause_id = stable_id(
                        "CV" if valid_from else "EXCERPT",
                        [source.id, proposal.page, start, proposal.quote, valid_from, valid_to],
                    )
                    if valid_from:
                        clause = ClauseVersion(
                            id=clause_id,
                            clause_id=stable_id("CL", [source.url, proposal.article]),
                            document=extraction.document_number or source.title,
                            article=proposal.article,
                            text=proposal.quote,
                            source_url=source.url,
                            source_sha256=source.sha256,
                            retrieved_at=datetime.now(UTC),
                            valid_from=valid_from,
                            valid_to=valid_to,
                            status_note="Unverified machine extraction; date interpretation, original PDF and current applicability require human review.",
                        )
                        graph.add_node(
                            clause_id, 1, "ClauseVersion", clause.model_dump(mode="json")
                        )
                    else:
                        graph.add_node(
                            clause_id,
                            1,
                            "ClauseExcerpt",
                            {
                                "text": proposal.quote,
                                "valid_from": None,
                                "verification_status": "to_be_verified",
                            },
                        )
                    graph.add_node(article_id, 1, "Article", {"article": proposal.article})
                    graph.link(source.id, "CONTAINS", article_id)
                    graph.link(
                        article_id, "HAS_VERSION" if valid_from else "HAS_EXCERPT", clause_id
                    )
                    graph.link(
                        clause_id,
                        "EXTRACTED_FROM",
                        source.id,
                        page=proposal.page,
                        start=start,
                        end=start + len(proposal.quote),
                    )
                    proposal_id = stable_id(
                        "PROPOSAL", [workspace["id"], clause_id, proposal.requirement]
                    )
                    concept_id = stable_id("CONCEPT", [workspace["id"], proposal.concept])
                    payload = {
                        **proposal.model_dump(mode="json"),
                        "id": proposal_id,
                        "source_id": source.id,
                        "source_url": source.url,
                        "source_sha256": source.sha256,
                        "clause_id": clause_id,
                        "valid_from": str(valid_from) if valid_from else None,
                        "valid_to": str(valid_to) if valid_to else None,
                        "quote_start": start,
                        "quote_end": start + len(proposal.quote),
                        "enabled": False,
                        "verification_status": "to_be_verified",
                        "runtime_contract": "requires_domain_pack_review",
                        "check_operation": "model_review",
                        "activation_date": None,
                    }
                    proposals[proposal_id] = payload
                    graph.add_node(proposal_id, 2, "RuleProposal", payload)
                    graph.add_node(concept_id, 2, "Concept", {"title": proposal.concept})
                    graph.link(proposal_id, "DERIVED_FROM", clause_id)
                    graph.link(proposal_id, "DETECTS", concept_id)
                    graph.link(
                        workbook_id,
                        "POTENTIALLY_SUBJECT_TO",
                        proposal_id,
                        applicability="pending_business_facts",
                    )
                    covered.add(proposal.topic_id)
                    for document in proposal.related_documents:
                        _reference(graph, clause_id, document)
                for relation in extraction.relations:
                    page = next((p["text"] for p in selected if p["page"] == relation.page), "")
                    if relation.quote not in page:
                        gaps.append(source.id + ":relation_quote_mismatch")
                        continue
                    target = _reference(graph, source.id, relation.target_document, relation.kind)
                    graph.link(
                        source.id,
                        "RELATION_EVIDENCE",
                        target,
                        relation_kind=relation.kind,
                        quote=relation.quote,
                        page=relation.page,
                        effective_on=str(relation.effective_on) if relation.effective_on else None,
                        verification_status="candidate",
                    )
            except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
                gaps.append(
                    f"{link.url}:{type(exc).__name__}:could not confirm updates from this source"
                )
                emit("source_gap", "Nguồn chưa đọc được; sẽ tìm bản khác nếu còn ngân sách.")
        if stop in ("time_budget", "source_budget", "rule_budget"):
            break
        stalls = stalls + 1 if not novelty else 0
        if stalls >= budget.stall_rounds:
            stop = "no_new_sources"
            break
    missing = tuple(t.id for t in plan.topics if t.id not in covered)
    if not missing and not _unresolved(graph) and stop == "round_budget":
        stop = "topic_coverage"
    emit(
        "done",
        f"Đã lưu {len(proposals)} rule đề xuất vào graph 3 lớp; tất cả chờ duyệt nguồn và phạm vi áp dụng.",
    )
    return _result(
        graph,
        proposals,
        plan.topics,
        missing,
        stop,
        gaps,
        calls,
        transport,
        started,
        budget,
        attempts,
    )


def _reference(graph, source, title, kind="REFERS_TO"):
    target = stable_id("UNRESOLVED", title)
    graph.add_node(
        target, 1, "UnresolvedDocument", {"title": title, "verification_status": "unresolved"}
    )
    graph.link(source, kind, target, verification_status="candidate")
    return target


def _date_appears(value, text):
    if value is None or text is None:
        return False
    return bool(
        re.search(
            rf"\b0?{value.day}\s*(?:/|-|tháng)\s*0?{value.month}\s*(?:/|-|năm)\s*{value.year}\b",
            text,
            re.IGNORECASE,
        )
        or value.isoformat() in text
    )


def _result(
    graph, proposals, topics, missing, stop, gaps, calls, transport, started, budget, attempts
):
    return {
        "graph": graph.as_dict(),
        "proposals": list(proposals.values()),
        "topics": [t.model_dump(mode="json") for t in topics],
        "missing_topics": list(missing),
        "stop_reason": stop,
        "gaps": list(dict.fromkeys(gaps)),
        "unresolved_documents": _unresolved(graph),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "sources_attempted": attempts,
        "budget": asdict(budget),
        "calls": calls,
        "model_events": list(getattr(transport, "events", [])),
        "executed_rule_count": 0,
        "legal_completeness_claimed": False,
        "status": "not_enough_information",
        "candidate_preview": True,
    }
