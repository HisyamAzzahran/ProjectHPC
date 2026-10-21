"""Real job lifecycle, durable records, exclusion, cancellation and scientific baselines."""
import json
import os
import threading
import time
from uuid import uuid4

import pandas as pd
import pytest

from benchmark import summarize
from core.data_manager import DataStore
from core.execution_manager import ExecutionManager
from core.simulation_engine import run_simulation


def config(workload=10003):
    return dict(algorithm="midpoint", method="multiprocessing", workload_size=workload,
                process_count=2, seed=0, chunk_size=997)


def test_completed_job_persistence_and_no_duplicate(tmp_path):
    manager = ExecutionManager(tmp_path)
    run_id = manager.start_simulation(**config())
    with pytest.raises(RuntimeError, match="already running"):
        manager.start_simulation(**config())
    result = manager.wait(30)
    assert result["status"] == "COMPLETED", result
    assert result["result"]["processed_units"] == 10003
    fresh = ExecutionManager(tmp_path)
    assert fresh.store.read(run_id)["status"] == "COMPLETED"
    assert fresh.store.export_frame().iloc[0].algorithm == "midpoint"
    for name in ("job.json", "result.json", "stdout.log", "stderr.log", "resources.csv"):
        assert (fresh.store.job_dir(run_id) / name).exists()


def test_cancellation_and_lock_release(tmp_path):
    manager = ExecutionManager(tmp_path)
    manager.start_simulation(**config(1_000_000_000))
    time.sleep(0.25)
    manager.cancel()
    assert manager.wait(20)["status"] == "CANCELLED"
    manager.start_simulation(**config())
    assert manager.wait(30)["status"] == "COMPLETED"


def test_interrupted_owner_recovery(tmp_path):
    store = DataStore(tmp_path)
    job_id = uuid4().hex
    store.save(dict(run_id=job_id, timestamp="2026-01-01T00:00:00+00:00", status="RUNNING", kind="simulation",
                    config=config(), owner_pid=os.getpid(), owner_created=0))
    fresh = ExecutionManager(tmp_path)
    assert fresh.store.read(job_id)["status"] == "INTERRUPTED"


def test_manager_failure_persists_useful_error(tmp_path, monkeypatch):
    import core.execution_manager as module

    def fail(**kwargs):
        raise RuntimeError("controlled execution failure")

    monkeypatch.setattr(module, "run_simulation", fail)
    manager = ExecutionManager(tmp_path)
    job_id = manager.start_simulation(**config())
    record = manager.wait(20)
    assert record["status"] == "FAILED"
    assert "controlled execution failure" in record["error_message"]
    assert "controlled execution failure" in (manager.store.job_dir(job_id) / "stderr.log").read_text()


def test_real_dual_benchmark_job_and_algorithm_baselines(tmp_path):
    manager = ExecutionManager(tmp_path)
    job_id = manager.start_benchmark(["monte_carlo", "midpoint"], ["sequential", "multiprocessing"],
                                     [10003], [1, 2], repeats=3, chunk_size=997)
    record = manager.wait(90)
    assert record["status"] == "COMPLETED", record
    directory = manager.store.job_dir(job_id)
    data = pd.read_csv(directory / "benchmark.csv")
    assert len(data) == 18
    summary = summarize(data)
    assert len(summary) == 6
    for algorithm in ("monte_carlo", "midpoint"):
        current = summary[summary.algorithm == algorithm]
        baseline = current[current.method == "sequential"].iloc[0]
        assert baseline.speedup == 1
        for row in current.itertuples():
            assert row.speedup == pytest.approx(baseline.median_end_to_end_seconds / row.median_end_to_end_seconds)
    assert (directory / "report.md").exists()
    assert len(list((directory / "figures").glob("*.png"))) == 13


def test_cancel_benchmark_marks_partial_dataset(tmp_path):
    manager = ExecutionManager(tmp_path)
    job_id = manager.start_benchmark(["monte_carlo", "midpoint"], ["sequential", "multiprocessing"],
                                     [1_000_000_000], [1, 2], repeats=3)
    time.sleep(0.4)
    manager.cancel()
    assert manager.wait(20)["status"] == "CANCELLED"
    metadata = manager.store.job_dir(job_id) / "benchmark.metadata.json"
    if metadata.exists():
        assert json.loads(metadata.read_text())["status"] == "cancelled"


def test_external_workspace_lock_prevents_contention(tmp_path):
    first = ExecutionManager(tmp_path)
    second = ExecutionManager(tmp_path)
    first.start_simulation(**config(1_000_000_000))
    try:
        with pytest.raises(RuntimeError, match="execution lock"):
            second.start_simulation(**config())
    finally:
        first.cancel()
        first.wait(20)
