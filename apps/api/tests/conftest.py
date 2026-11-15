"""The suite never reads or mutates a developer's database or hosted AI account."""
import os
import tempfile
from pathlib import Path

_test_dir = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(_test_dir.name) / 'tests.db')
for variable in ('LLM_API_KEY', 'GEMINI_API_KEY'):
    os.environ[variable] = ''

from app.db import init_db
init_db()
