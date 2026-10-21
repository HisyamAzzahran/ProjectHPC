"""Standard external execution interface shared by benchmarks and the dashboard."""
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from uuid import uuid4
from time import perf_counter

from environment import ROOT, find_mpiexec
from core.process_control import ProcessContainer
from core.system_monitor import TreeSampler
from core.workload_manager import validate_config


class ExecutionCancelled(RuntimeError):
    pass


def child_environment():
    env = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[name] = "1"
    env["PYTHONUTF8"] = "1"
    return env


def simulation_command(algorithm, method, workload_size, process_count, seed, chunk_size,
                       launcher=None, allow_oversubscribe=False):
    validate_config(algorithm, method, workload_size, process_count, seed, chunk_size, allow_oversubscribe)
    scripts = {"sequential": "sequential.py", "multiprocessing": "multiprocessing_pi.py", "mpi": "mpi_pi.py"}
    command = [sys.executable, str(ROOT / scripts[method]), "--algorithm", algorithm,
               "--workload", str(workload_size), "--seed", str(seed), "--chunk-size", str(chunk_size), "--json"]
    if method == "multiprocessing":
        command += ["--processes", str(process_count)]
    if method != "sequential" and allow_oversubscribe:
        command += ["--allow-oversubscribe"]
    if method == "mpi":
        launcher = launcher or find_mpiexec()
        if not launcher:
            raise RuntimeError("MPI launcher unavailable; install the matching runtime or select another method")
        command = [launcher, "-n", str(process_count), *command]
    return command


def execute_command(command, timeout=300, cancel_event=None, on_sample=None, interval=0.1, log_directory=None):
    """File-backed capture prevents pipe deadlocks. All timers include orchestration overhead."""
    cancel_event = cancel_event or threading.Event()
    if cancel_event.is_set():
        raise ExecutionCancelled("cancelled before process launch")
    env = child_environment()
    with tempfile.TemporaryDirectory(prefix="hpc-processes-") as registry, \
         (tempfile.TemporaryFile() if log_directory is None else (Path(log_directory) / "stdout.log").open("w+b")) as stdout, \
         (tempfile.TemporaryFile() if log_directory is None else (Path(log_directory) / "stderr.log").open("w+b")) as stderr:
        token = uuid4().hex
        parents = json.loads(env.get("HPC_PARENT_REGISTRIES", "[]"))
        if env.get("HPC_PROCESS_REGISTRY") and env.get("HPC_JOB_TOKEN"):
            parents.append([env["HPC_PROCESS_REGISTRY"], env["HPC_JOB_TOKEN"]])
        env["HPC_PARENT_REGISTRIES"] = json.dumps(parents)
        env.update(HPC_PROCESS_REGISTRY=registry, HPC_JOB_TOKEN=token)
        start = perf_counter()
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        container = ProcessContainer(process.pid)
        sampler = TreeSampler(process.pid, registry, token)
        reason = None
        try:
            while True:
                row, tree = sampler.sample()
                if on_sample:
                    on_sample(row, tree, process.pid)
                if cancel_event.is_set():
                    reason = "cancelled"
                    break
                if perf_counter() - start > timeout:
                    reason = "timeout"
                    break
                try:
                    process.wait(timeout=interval)
                    break
                except subprocess.TimeoutExpired:
                    pass
        finally:
            (Path(registry) / "cancel.request").touch()
            registered = sampler.registered_processes()
            for candidate in registered:
                sampler.observed[(candidate.pid, candidate.create_time())] = candidate
            container.close(sampler.observed.values())
            process.wait(timeout=10)
        elapsed = perf_counter() - start
        stdout.seek(0)
        stderr.seek(0)
        output, errors = stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")
    if reason == "cancelled":
        raise ExecutionCancelled("execution cancelled; owned subprocess tree terminated")
    if reason == "timeout":
        raise TimeoutError(f"execution exceeded {timeout} seconds; owned subprocess tree terminated")
    return dict(returncode=process.returncode, stdout=output, stderr=errors,
                end_to_end_seconds=elapsed, resource_samples=sampler.samples,
                containment=container.containment + " + token/birth-verified process registry", **sampler.metrics(elapsed))


def run_simulation(algorithm="monte_carlo", method="sequential", workload_size=1_000_000,
                   process_count=1, seed=2026, chunk_size=100_000, launcher=None,
                   timeout=300, allow_oversubscribe=False, cancel_event=None, on_sample=None, log_directory=None):
    command = simulation_command(algorithm, method, workload_size, process_count, seed, chunk_size,
                                 launcher, allow_oversubscribe)
    execution = execute_command(command, timeout, cancel_event, on_sample, log_directory=log_directory)
    if execution["returncode"]:
        raise RuntimeError(f"Command exited {execution['returncode']}: {execution['stderr']}\n{execution['stdout']}")
    try:
        result = json.loads(execution["stdout"].strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Expected one structured result: {execution['stdout']}") from exc
    expected = dict(algorithm=algorithm, method=method, samples=workload_size, processes=process_count,
                    seed=seed, chunk_size=chunk_size, processed_samples=workload_size, status="COMPLETED")
    if any(result.get(key) != value for key, value in expected.items()):
        raise RuntimeError(f"Result configuration/accounting mismatch: {result}")
    if len(set(result["worker_pids"])) != process_count:
        raise RuntimeError("requested workers/ranks were not initialized")
    result.update(execution)
    result.update(execution_time=execution["end_to_end_seconds"], timing_scope="end_to_end")
    return result
