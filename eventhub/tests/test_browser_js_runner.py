"""Include the existing browser interaction checks in the one-command pytest suite."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_existing_browser_interactions():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the existing JavaScript interaction tests")
    script = Path(__file__).with_name("browser_interactions.test.cjs")
    result = subprocess.run([node, "--test", str(script)], capture_output=True, text=True,
                            timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
