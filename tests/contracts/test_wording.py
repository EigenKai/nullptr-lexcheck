import re
import unicodedata
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FORBIDDEN = re.compile(r"\b(compliant|approved)\b|hợp lệ|đúng luật", re.IGNORECASE)


def test_product_api_does_not_use_prohibited_verdicts():
    client = TestClient(app)
    responses = [client.get(p) for p in ("/health", "/api/demo", "/api/history")]
    responses += [client.post("/api/check", json={"text": "approved"})]
    for response in responses:
        assert not FORBIDDEN.search(unicodedata.normalize("NFC", response.text))


def test_ui_production_source_avoids_prohibited_verdicts():
    root = Path(__file__).resolve().parents[2] / "ui/src"
    for path in root.rglob("*"):
        if (
            path.is_file()
            and path.suffix in (".tsx", ".ts", ".jsx", ".js", ".html")
            and ".test." not in path.name
        ):
            assert not FORBIDDEN.search(unicodedata.normalize("NFC", path.read_text()))
