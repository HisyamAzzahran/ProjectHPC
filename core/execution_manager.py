"""One durable background job shared across Streamlit reruns and browser sessions."""
import csv
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import psutil

from core.data_manager import DataStore, atomic_json
from core.simulation_engine import ExecutionCancelled, execute_command, run_simulation
from core.workload_manager import validate_config
from environment import ROOT

ACTIVE = {"STARTING", "RUNNING"}
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class ExecutionManager:
    def __init__(self, storage=None):
        self.store = DataStore(storage)
        self.lock = threading.RLock()
        self.cancel_event = threading.Event()
        self.thread, self.active_id = None, None
        self._lock_handle = None
        self._recover()

    def _acquire_workspace(self):
        # OS releases the lock when the dashboard crashes. Also serializes other server instances.
        handle = (self.store.root / ".execution.lock").open("a+b")
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise RuntimeError("another HPC job owns the workspace execution lock") from exc
        self._lock_handle = handle

    def _release_workspace(self):
        if self._lock_handle:
            self._lock_handle.close()
            self._lock_handle = None

    def _recover(self):
        for record in self.store.history():
            if record["status"] not in ACTIVE:
                continue
            owner = record.get("owner_pid")
            try:
                process = psutil.Process(owner)
                live = abs(process.create_time() - record.get("owner_created", 0)) < 0.01
            except (psutil.Error, TypeError):
                live = False
            if live:
                self.active_id = record["run_id"]
                continue
            # A previous server ended: never infer completion from a leftover result file.
            record.update(status="INTERRUPTED", finished_at=timestamp(),
                          error_message="dashboard owner stopped before the job reached a terminal state")
            self.store.save(record)

    def current(self):
        with self.lock:
            return self.store.read(self.active_id) if self.active_id else None

    def busy(self):
        record = self.current()
        return bool(record and record["status"] in ACTIVE)

    def start_simulation(self, **config):
        validate_config(**config)
        return self._start("simulation", config)

    def start_benchmark(self, algorithms, methods, workloads, processes, repeats=3, chunk_size=100_000, seed=2026):
        if not algorithms or not methods or not workloads or not processes or "sequential" not in methods:
            raise ValueError("select algorithms, workloads, processes, and a sequential baseline")
        if not isinstance(repeats, int) or repeats < 1:
            raise ValueError("repetitions must be positive")
        for algorithm in algorithms:
            for method in methods:
                for workload in workloads:
                    for p in ([1] if method == "sequential" else processes):
                        validate_config(algorithm, method, int(workload), int(p), int(seed), int(chunk_size))
        return self._start("benchmark", dict(algorithms=algorithms, methods=methods, workloads=workloads,
                                           processes=processes, repeats=repeats, chunk_size=chunk_size, seed=seed))

    def _start(self, kind, config):
        with self.lock:
            if self.busy():
                raise RuntimeError("a computational job is already running")
            self._acquire_workspace()
            try:
                job_id = uuid4().hex
                owner = psutil.Process()
                record = dict(run_id=job_id, timestamp=timestamp(), kind=kind, config=config, status="STARTING",
                              owner_pid=owner.pid, owner_created=owner.create_time(), error_message=None,
                              result=None, elapsed_seconds=0.0)
                self.store.save(record)
                self.active_id = job_id
                self.cancel_event = threading.Event()
                self.thread = threading.Thread(target=self._run, args=(job_id,), daemon=True, name=f"hpc-{job_id[:8]}")
                self.thread.start()
            except BaseException:
                self._release_workspace()
                raise
            return job_id

    def cancel(self):
        with self.lock:
            if self.busy():
                self.cancel_event.set()
                # File signal also works when another browser session restores this manager.
                (self.store.job_dir(self.active_id) / "cancel.request").touch()

    def wait(self, timeout=60):
        if self.thread:
            self.thread.join(timeout)
        return self.current()

    def _run(self, job_id):
        record = self.store.read(job_id)
        directory = self.store.job_dir(job_id)
        start = perf_counter()
        last_saved = [0.0]
        try:
            record["status"] = "RUNNING"
            self.store.save(record)
            with (directory / "resources.csv").open("w", newline="", encoding="utf-8") as resource_file:
                writer = None

                def sample(row, tree, pid):
                    nonlocal writer
                    if (directory / "cancel.request").exists():
                        self.cancel_event.set()
                    if writer is None:
                        writer = csv.DictWriter(resource_file, fieldnames=list(row))
                        writer.writeheader()
                    writer.writerow(row)
                    resource_file.flush()
                    if perf_counter() - last_saved[0] >= 1:
                        record.update(elapsed_seconds=perf_counter() - start, resources=row,
                                      process_tree=tree, child_pid=pid)
                        self.store.save(record)
                        last_saved[0] = perf_counter()

                if record["kind"] == "simulation":
                    output = run_simulation(**record["config"], cancel_event=self.cancel_event, on_sample=sample,
                                            timeout=1800, log_directory=directory)
                else:
                    config = record["config"]
                    csv_path = directory / "benchmark.csv"
                    command = [sys.executable, str(ROOT / "benchmark.py"), "--algorithms", *config["algorithms"],
                               "--methods", *config["methods"], "--workloads", *map(str, config["workloads"]),
                               "--processes", *map(str, config["processes"]), "--repeats", str(config["repeats"]),
                               "--chunk-size", str(config["chunk_size"]), "--seed", str(config["seed"]), "--output", str(csv_path)]
                    output = execute_command(command, timeout=7200, cancel_event=self.cancel_event,
                                             on_sample=sample, interval=0.2, log_directory=directory)
                    if output["returncode"]:
                        raise RuntimeError(output["stderr"] + output["stdout"])
                    output["benchmark_csv"] = str(csv_path)
                    # Generate matching export artifacts after computation, outside benchmark timings.
                    from plot_results import generate_plots
                    from report_results import generate_report
                    if self.cancel_event.is_set() or (directory / "cancel.request").exists():
                        raise ExecutionCancelled("benchmark cancelled before artifact generation")
                    generate_plots(csv_path, directory / "figures", cancel_event=self.cancel_event)
                    generate_report(csv_path, directory / "report.md")
                (directory / "stdout.log").write_text(output.pop("stdout", ""), encoding="utf-8")
                (directory / "stderr.log").write_text(output.pop("stderr", ""), encoding="utf-8")
                output.pop("resource_samples", None)
                if self.cancel_event.is_set():
                    raise ExecutionCancelled("cancelled before recording completion")
                atomic_json(directory / "result.json", output)
                record.update(status="COMPLETED", result=output)
        except ExecutionCancelled as exc:
            record.update(status="CANCELLED", error_message=str(exc))
        except BaseException as exc:
            record.update(status="FAILED", error_message=str(exc))
            with (directory / "stderr.log").open("a", encoding="utf-8") as error_file:
                error_file.write("\n" + str(exc))
        finally:
            record.update(finished_at=timestamp(), elapsed_seconds=perf_counter() - start)
            self.store.save(record)
            metadata = directory / "benchmark.metadata.json"
            if record["status"] != "COMPLETED" and metadata.exists():
                document = json.loads(metadata.read_text(encoding="utf-8"))
                document["status"] = record["status"].lower()
                atomic_json(metadata, document)
            self._release_workspace()


# Imported once per interpreter: survives Streamlit reruns and new browser sessions.
_manager = None
_manager_lock = threading.Lock()


def get_manager():
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ExecutionManager()
        return _manager
