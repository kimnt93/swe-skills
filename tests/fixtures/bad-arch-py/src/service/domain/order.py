"""The domain must not do I/O: lint-imports must flag this."""

import psycopg  # noqa: F401
