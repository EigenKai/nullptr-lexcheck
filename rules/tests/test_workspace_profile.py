"""Profile output must cite selected company inputs; no law or industry defaults."""

from types import SimpleNamespace

import pytest

from rules.workspace_profile import infer_profile
from rules.workspaces import WorkspaceStore


def test_generic_profile_uses_only_selected_company_context_and_records_provenance(tmp_path):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Different sector", description="Doanh nghiệp sửa chữa xe đạp.")
    store.add_document(workspace["id"], "legal", "law.txt", b"LAW-NOT-A-COMPANY-FACT")
    captured = []

    class Client:
        model = "injected-test-model"

        def generate(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(
                status="live",
                parsed={
                    "summary": "Sửa chữa xe đạp",
                    "sector": "Dịch vụ sửa chữa",
                    "activities": ["Sửa xe đạp"],
                    "jurisdiction": None,
                    "facts": [
                        {
                            "statement": "Sửa xe đạp",
                            "document_id": "USER-DESCRIPTION",
                            "page": 1,
                            "quote": "sửa chữa xe đạp",
                        }
                    ],
                    "unknowns": ["Địa phương"],
                },
                key="test-cache-key",
                calls=1,
            )

    result = infer_profile(store, workspace["id"], Client())
    assert result["sector"] == "Dịch vụ sửa chữa"
    assert result["provenance"]["kind"] == "llm_api"
    assert result["provenance"]["model_calls"] == 1
    assert "LAW-NOT-A-COMPANY-FACT" not in str(captured[0]["payload"])
    assert "rental_housing" not in str(captured[0]["payload"])
    assert store.get(workspace["id"])["profile"] == result


def test_profile_without_reviewed_inputs_never_calls_model(tmp_path):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Empty")
    with pytest.raises(ValueError, match="Select reviewed"):
        infer_profile(store, workspace["id"], object())
