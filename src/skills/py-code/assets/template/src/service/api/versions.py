"""The API versions this service serves. Add "v2" here when /v2 exists: every
listed version is a route group (/v1, /v2) and is shown in `api_versions` by
/healthz (see routes/health.py).
"""

from __future__ import annotations

API_VERSIONS = ("v1",)
