"""Layer 0 runs the actual reviewed engine, validator, state and HTTP routes."""

from intake.tests.test_api import run_dossier_flow


def test_layer0_smoke(api):
    run_dossier_flow(api)
