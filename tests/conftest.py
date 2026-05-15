from __future__ import annotations

import os
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars")
os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("REDIS_PASSWORD", "test-redis-password")
