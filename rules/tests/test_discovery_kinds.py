import pytest
from pydantic import ValidationError

from contracts.models import Record
from rules.discovery_models import CheckPlan


def test_generated_reference_kinds_use_the_canonical_record_schema():
    schema = CheckPlan.model_json_schema()
    assert (
        schema["properties"]["reference_kind"]["anyOf"][0]["enum"]
        == Record.model_json_schema()["properties"]["kind"]["enum"]
    )
    with pytest.raises(ValidationError):
        CheckPlan(operation="required_reference", reference_kind="ad_content_confirmation")
