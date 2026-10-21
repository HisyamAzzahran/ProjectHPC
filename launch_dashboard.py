"""One-command local launcher, using the current virtual-environment interpreter."""
import argparse
import importlib.util
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def open_when_ready(url, process):
    for _ in range(100):
        if process.poll() is not None:
            return
        try:
            with urllib.request.urlopen(url + "/_stcore/health", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(0.2)


def main():
    local_python = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if sys.prefix == sys.base_prefix and local_python.is_file() and Path(sys.executable).resolve() != local_python.resolve():
        print(f"Using workspace virtual environment: {local_python}", flush=True)
        return subprocess.call([str(local_python), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help="run local server without opening a browser")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if sys.version_info < (3, 11) or sys.maxsize <= 2**32:
        parser.error("64-bit Python 3.11 or newer is required")
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    missing = [name for name in ("streamlit", "plotly", "psutil", "numpy", "pandas", "matplotlib")
               if importlib.util.find_spec(name) is None]
    if missing:
        parser.exit(1, f"Missing dependencies: {', '.join(missing)}\nRun: {sys.executable} -m pip install -r requirements.txt\n")
    if sys.prefix == sys.base_prefix:
        print("A virtual environment is recommended; the launcher uses:", sys.executable, flush=True)
    for name in ("results", "results/jobs", "figures", "logs", ".cache"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            parser.exit(1, f"Port {args.port} is already in use. Choose --port with a free local port.\n")
    url = f"http://localhost:{args.port}"
    command = [sys.executable, "-m", "streamlit", "run", str(ROOT / "dashboard" / "app.py"),
               "--server.address", "127.0.0.1", "--server.port", str(args.port), "--server.headless", "true"]
    print(f"HPC Parallel Computing & Performance Lab\nInterpreter: {sys.executable}\nLocal URL: {url}", flush=True)
    process = subprocess.Popen(command, cwd=ROOT)
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url, process), daemon=True).start()
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
