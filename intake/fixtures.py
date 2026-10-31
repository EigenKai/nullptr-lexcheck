from pathlib import Path

from contracts.models import DemoBundle

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data/fixtures/demo.json"


def load_demo() -> DemoBundle:
    return DemoBundle.model_validate_json(FIXTURE_PATH.read_text())
