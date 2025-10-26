"""Global pytest configuration for the test suite."""
from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    "dev",
    settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=(HealthCheck.too_slow,),
    ),
)
settings.register_profile(
    "ci",
    settings(
        max_examples=200,
        suppress_health_check=(HealthCheck.too_slow,),
    ),
)

profile = os.getenv("HYPOTHESIS_PROFILE")
if profile:
    settings.load_profile(profile)
elif os.getenv("CI"):
    settings.load_profile("ci")
else:
    settings.load_profile("dev")
