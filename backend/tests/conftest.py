"""Point the test suite at a throwaway SQLite file.

Without this, tests seed and read ``data/edmonton_lens.db``, so their results
depend on whatever the last pipeline run left there.
"""

from __future__ import annotations

import os
import tempfile

_TEST_DB = os.path.join(tempfile.mkdtemp(prefix="edmontonlens-test-"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
# Keep tests on the local DB even when .env has BigQuery configured.
os.environ["GCP_PROJECT_ID"] = ""
