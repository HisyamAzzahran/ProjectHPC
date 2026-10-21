"""Verify actual local HTTP serving, including global-Python venv selection."""
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psutil
import pytest

from core.process_control import ProcessContainer
from environment import ROOT


GLOBAL_PYTHON = Path(sys.base_prefix) / ("python.exe" if sys.platform == "win32" else "bin/python3")


@pytest.mark.parametrize("interpreter", [sys.executable, str(GLOBAL_PYTHON)])
def test_one_command_launcher_serves_real_http(interpreter, tmp_path):
    if not Path(interpreter).is_file():
        pytest.skip("base interpreter path unavailable")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    logfile = tmp_path / "server.log"
    with logfile.open("wb") as output:
        process = subprocess.Popen([interpreter, str(ROOT / "launch_dashboard.py"), "--no-browser", "--port", str(port)],
                                   cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        container = ProcessContainer(process.pid)
        observed = []
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                assert process.poll() is None, logfile.read_text(errors="replace")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=0.5) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                pytest.fail("server health never became ready: " + logfile.read_text(errors="replace"))
            with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=3) as response:
                assert response.status == 200
                assert b"streamlit" in response.read().lower()
            observed = psutil.Process(process.pid).children(recursive=True)
            assert observed
        finally:
            container.close(observed)
            process.wait(timeout=15)
        assert all(not p.is_running() for p in observed)


def test_launcher_rejects_invalid_port():
    completed = subprocess.run([sys.executable, str(ROOT / "launch_dashboard.py"), "--no-browser", "--port", "0"],
                               cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert completed.returncode == 2
    assert "port must be between" in completed.stderr
