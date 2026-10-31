"""Public-source PDF OCR adapter tests using injected SDK responses."""

from rules.tests.test_discovery_client import Client


def test_pdf_transcription_uses_file_input_and_workspace_scoped_cache(tmp_path):
    from detect.client import DiscoveryTransport

    client = Client(
        {"pages": [{"page": 1, "text": "Điều 1. Văn bản thử nghiệm."}], "uncertainties": []}
    )
    adapter = DiscoveryTransport(client=client, model="test", cache_dir=tmp_path)
    import base64

    payload = {
        "workspace_id": "WS-one",
        "source_url": "https://vanban.chinhphu.vn/example",
        "pdf_base64": base64.b64encode(b"%PDF-test").decode(),
        "original_page_numbers": [7],
    }
    schema = {
        "type": "object",
        "properties": {
            "pages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"page": {"type": "integer"}, "text": {"type": "string"}},
                },
            },
            "uncertainties": {"type": "array", "items": {"type": "string"}},
        },
    }
    result = adapter.complete("ocr", payload, schema, timeout_s=5)
    assert result["pages"][0]["page"] == 1
    call = client.calls[0]
    assert "tools" not in call
    assert call["store"] is False
    assert call["input"][0]["content"][0]["type"] == "input_file"
    assert call["input"][0]["content"][0]["file_data"].startswith("data:application/pdf;base64,")
    adapter.complete("ocr", payload, schema, timeout_s=5)
    assert len(client.calls) == 1
    adapter.complete("ocr", {**payload, "workspace_id": "WS-two"}, schema, timeout_s=5)
    assert len(client.calls) == 2


def test_housing_extraction_does_not_use_advertising_pack_instructions():
    from detect.client import DiscoveryTransport

    client = Client({"proposals": []})
    DiscoveryTransport(client=client, model="test").complete(
        "extract", {"domain": "rental_housing"}, {}, timeout_s=5
    )
    instruction = client.calls[0]["instructions"]
    assert "housing" in instruction
    assert "Canonical check_type values are warning" not in instruction
