"""Phase gate: run all six real algorithm/model configurations before UI work."""
import math
import threading
import time

import psutil
import pytest

from algorithms.midpoint_integration import iter_tasks
from core.simulation_engine import ExecutionCancelled, execute_command, run_simulation
from core.workload_manager import validate_config
from environment import find_mpiexec
from sequential import simulate


@pytest.mark.parametrize("algorithm", ["monte_carlo", "midpoint"])
@pytest.mark.parametrize("method", ["sequential", "multiprocessing", "mpi"])
def test_six_real_configurations(algorithm, method):
    if method == "mpi" and not find_mpiexec():
        pytest.skip("external MPI launcher unavailable")
    p = 1 if method == "sequential" else 2
    result = run_simulation(algorithm, method, 100003, p, 2026, 997)
    baseline = simulate(100003, 2026, 997, algorithm)
    assert result["processed_units"] == 100003
    assert result["status"] == "COMPLETED"
    assert len(set(result["worker_pids"])) == p
    assert set(result["working_pids"]) <= set(result["worker_pids"])
    assert all(not psutil.pid_exists(pid) for pid in result["worker_pids"])
    if method == "mpi":
        assert result["world_size"] == p
    if algorithm == "monte_carlo":
        assert result["hits"] == baseline["hits"]
        assert result["pi_estimate"] == baseline["pi_estimate"]
    else:
        assert result["hits"] is None and result["random_seed"] is None
        assert abs(result["pi_estimate"] - math.pi) < 1e-10
        assert result["pi_estimate"] == pytest.approx(baseline["pi_estimate"], abs=1e-13)
    assert 0 < result["compute_seconds"] < result["end_to_end_seconds"]
    assert result["peak_rss_mb"] > 0


def test_midpoint_convergence_and_independent_scalar_reference():
    errors = [simulate(n, chunk_size=7, algorithm="midpoint")["absolute_error"] for n in (10, 100, 1000)]
    assert errors[0] > errors[1] > errors[2]
    assert errors[0] / errors[1] == pytest.approx(100, rel=0.01)
    n = 37
    scalar = math.fsum(4 / (1 + ((i + 0.5) / n)**2) for i in range(n)) / n
    assert simulate(n, chunk_size=7, algorithm="midpoint")["pi_estimate"] == pytest.approx(scalar, abs=1e-15)


@pytest.mark.parametrize("processes", [1, 2, 4, 20])
def test_interval_partition_exactly_once(processes):
    all_indices = []
    for rank in range(processes):
        for _, start, count, _ in iter_tasks(103, 11, rank, processes):
            all_indices.extend(range(start, start + count))
    assert sorted(all_indices) == list(range(103))


def test_monte_carlo_different_seeds_and_legacy_stream():
    assert simulate(100000)["hits"] == 78676
    zero = run_simulation("monte_carlo", "multiprocessing", 1003, 2, 0, 97)
    other = simulate(1003, 72, 97)
    assert zero["hits"] == simulate(1003, 0, 97)["hits"]
    assert zero["hits"] != other["hits"]


def test_zero_hits_is_a_valid_small_monte_carlo_result():
    # With one point, an outside point legitimately gives pi_hat=0.
    from monte_carlo import count_hits
    seed = next(seed for seed in range(100) if count_hits((0, 1, seed))[0] == 0)
    result = run_simulation("monte_carlo", "sequential", 1, 1, seed, 10)
    assert result["hits"] == 0 and result["pi_estimate"] == 0
    assert result["processed_units"] == 1 and result["status"] == "COMPLETED"


@pytest.mark.parametrize("changes", [{"workload_size": 0}, {"process_count": 0}, {"chunk_size": 0},
                                     {"seed": -1}, {"process_count": 100000}])
def test_invalid_inputs(changes):
    config = dict(algorithm="midpoint", method="multiprocessing", workload_size=10,
                  process_count=2, seed=2026, chunk_size=7)
    config.update(changes)
    with pytest.raises(ValueError):
        validate_config(**config)


def test_cancel_simulation_cleans_real_process_tree():
    cancel = threading.Event()
    seen = set()

    def sample(row, tree, pid):
        seen.update(item["pid"] for item in tree)
        if row["elapsed_seconds"] > 0.5:
            cancel.set()

    with pytest.raises(ExecutionCancelled):
        run_simulation("monte_carlo", "multiprocessing", 1_000_000_000, 2,
                       cancel_event=cancel, on_sample=sample)
    assert seen
    assert all(not psutil.pid_exists(pid) for pid in seen)


def test_command_failure_and_timeout():
    import sys

    result = execute_command([sys.executable, "-c", "raise RuntimeError('deliberate test error')"])
    assert result["returncode"] != 0 and "deliberate test error" in result["stderr"]
    with pytest.raises(TimeoutError):
        execute_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.2)


@pytest.mark.skipif(not find_mpiexec(), reason="external MPI launcher unavailable")
def test_cancel_mpi_including_detached_registered_ranks():
    cancel, seen = threading.Event(), set()

    def sample(row, tree, pid):
        seen.update(item["pid"] for item in tree)
        if row["elapsed_seconds"] > 0.65 and len(tree) >= 4:
            cancel.set()

    with pytest.raises(ExecutionCancelled):
        run_simulation("monte_carlo", "mpi", 1_000_000_000, 2, cancel_event=cancel,
                       on_sample=sample, timeout=10)
    assert len(seen) >= 4
    assert all(not psutil.pid_exists(pid) for pid in seen)


@pytest.mark.skipif(not find_mpiexec(), reason="external MPI launcher unavailable")
def test_mpi_resources_cover_registered_ranks():
    observed = set()

    def sample(row, tree, pid):
        observed.update(item["pid"] for item in tree)

    result = run_simulation("monte_carlo", "mpi", 1_000_003, 2, on_sample=sample)
    assert set(result["worker_pids"]) <= observed
    assert result["cpu_mean_percent"] > 0
    assert result["peak_rss_mb"] > 40


@pytest.mark.parametrize("algorithm", ["monte_carlo", "midpoint"])
@pytest.mark.parametrize("method", ["sequential", "multiprocessing", "mpi"])
def test_all_six_human_readable_cli_outputs(algorithm, method):
    import subprocess
    import sys
    from environment import ROOT
    scripts = {"sequential": "sequential.py", "multiprocessing": "multiprocessing_pi.py", "mpi": "mpi_pi.py"}
    command = [sys.executable, str(ROOT / scripts[method]), "--algorithm", algorithm,
               "--workload", "1003", "--chunk-size", "97"]
    if method == "multiprocessing":
        command += ["--processes", "2"]
    if method == "mpi":
        if not find_mpiexec():
            pytest.skip("external MPI launcher unavailable")
        command = [find_mpiexec(), "-n", "2", *command]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.count("Estimated pi:") == 1
    assert "Compute region:" in completed.stdout
    if algorithm == "midpoint":
        assert "Processed integration intervals: 1,003" in completed.stdout
