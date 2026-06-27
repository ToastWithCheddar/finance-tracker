"""BE-RL-001 — shared SlowAPI limiter instance.

`backend/app/main.py` historically built its own `Limiter` and stashed it on
`app.state.limiter`, but no route ever applied `@limiter.limit(...)`. This
module exposes a single module-level limiter so route files can decorate
endpoints without circular-importing `main`.

`main.py` re-uses this same instance to register the SlowAPI middleware and
the `RateLimitExceeded` handler, so there is one source of truth.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def _key_func(request):  # pragma: no cover - thin wrapper
    return get_remote_address(request)


# `enabled` flips with the global RATE_LIMITING toggle — when False the limiter
# becomes a no-op which is what local devs expect. Default is now True
# (BE-RL-001 / BE-SEC-005).
limiter = Limiter(
    key_func=_key_func,
    enabled=bool(getattr(settings, "RATE_LIMITING", True)),
    default_limits=[],
)
