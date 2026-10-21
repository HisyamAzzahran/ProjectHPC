"""Read-only environment inspection; no registry writes or system configuration."""

import ctypes
import importlib.metadata
import json
import os
import platform
import shutil
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

from monte_carlo import cpu_limit

ROOT = Path(__file__).resolve().parent


def find_mpiexec(explicit=None):
    if explicit:
        path = shutil.which(str(explicit))
        if path:
            return str(Path(path).resolve())
        raise FileNotFoundError(f"MPI launcher not found: {explicit}")
    # Prefer the runtime beside this interpreter rather than a different system MPI.
    local = Path(sys.prefix) / "Library" / "bin" / "mpiexec.exe"
    return str(local) if local.is_file() else shutil.which("mpiexec")


def windows_hardware():
    details = {}
    if os.name != "nt":
        return details
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            details["cpu_name"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            for name in ("ProductName", "DisplayVersion", "CurrentBuildNumber"):
                details[name] = winreg.QueryValueEx(key, name)[0]
    except OSError as exc:
        details["registry_inspection_error"] = str(exc)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    length = ctypes.c_ulong()
    kernel.GetLogicalProcessorInformationEx(0, None, ctypes.byref(length))
    buffer = ctypes.create_string_buffer(length.value)
    if kernel.GetLogicalProcessorInformationEx(0, buffer, ctypes.byref(length)):
        offset = cores = 0
        while offset < length.value:
            relationship, size = struct.unpack_from("II", buffer.raw, offset)
            if size == 0:
                break
            cores += relationship == 0
            offset += size
        details["physical_cores"] = cores

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in
            ("total_physical", "available_physical", "total_page", "available_page",
             "total_virtual", "available_virtual", "available_extended")
        ]

    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    if kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):
        details["ram_bytes"] = memory.total_physical
    return details


def inspect_environment():
    packages = {}
    for name in ("numpy", "pandas", "matplotlib", "mpi4py", "impi-rt", "streamlit", "plotly", "psutil", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    info = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                python=sys.version, interpreter=sys.executable, platform=platform.platform(),
                architecture=platform.machine(), logical_cpus=os.cpu_count(),
                available_logical_cpus=cpu_limit(), packages=packages,
                mpi_launcher=find_mpiexec(), hardware=windows_hardware(),
                thread_environment={k: os.environ.get(k) for k in
                                    ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")})
    # Inspect MPI in a child so the benchmark controller never initializes MPI.
    import subprocess

    try:
        result = subprocess.run(
            [sys.executable, "-c", "from mpi4py import MPI; print(MPI.Get_library_version())"],
            capture_output=True, text=True, timeout=30, check=True
        )
        info["mpi_library"] = result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        info["mpi_error"] = str(exc)
    return info


if __name__ == "__main__":
    print(json.dumps(inspect_environment(), indent=2))

