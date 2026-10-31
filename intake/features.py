"""All later layers are off by default; implementation stays behind these gates."""

import os

from contracts.models import FeatureFlags


def feature_flags(layer0_ready: bool = False) -> FeatureFlags:
    return FeatureFlags(
        layer0_ready=layer0_ready,
        layer1=os.getenv("LEXCHECK_LAYER1_ENABLED", "0") == "1",
        layer2=os.getenv("LEXCHECK_LAYER2_ENABLED", "0") == "1",
        layer3=os.getenv("LEXCHECK_LAYER3_ENABLED", "0") == "1",
    )
