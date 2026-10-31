"""Layer 0 runs the actual reviewed engine, validator, state and HTTP routes."""

from intake.tests.test_api import run_dossier_flow
from intake.tests.test_chat_runtime import run_layer1_chat_smoke


def test_layer0_smoke(api):
    run_dossier_flow(api)


def test_layer1_smoke(api, monkeypatch, tmp_path):
    run_layer1_chat_smoke(api, monkeypatch, tmp_path)
