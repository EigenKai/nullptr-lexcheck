"""All later layers are off by default; implementation stays behind these gates."""

import os

from contracts.models import FeatureFlags


def feature_flags(layer0_ready: bool = False) -> FeatureFlags:
    first = layer0_ready and os.getenv("LEXCHECK_LAYER1_ENABLED", "0") == "1"
    second = first and os.getenv("LEXCHECK_LAYER2_ENABLED", "0") == "1"
    third = second and os.getenv("LEXCHECK_LAYER3_ENABLED", "0") == "1"
    return FeatureFlags(
        layer0_ready=layer0_ready,
        layer1=first,
        layer2=second,
        layer3=third,
    )
