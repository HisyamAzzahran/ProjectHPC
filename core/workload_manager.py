"""Common algorithm dispatch and numerical aggregation."""
import math
import os
from datetime import datetime, timezone
from uuid import uuid4

from algorithms import midpoint_integration, monte_carlo
from monte_carlo import cpu_limit

ALGORITHMS = ("monte_carlo", "midpoint")
METHODS = ("sequential", "multiprocessing", "mpi")
UNITS = {"monte_carlo": "random samples", "midpoint": "integration intervals"}


def validate_config(algorithm, method, workload_size, process_count=1, seed=2026,
                    chunk_size=100_000, allow_oversubscribe=False):
    if algorithm not in ALGORITHMS or method not in METHODS:
        raise ValueError("unsupported algorithm or execution method")
    for name, value in (("workload", workload_size), ("processes", process_count), ("chunk size", chunk_size)):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= 2**63 - 1:
            raise ValueError(f"{name} must be a positive integer no larger than 2^63 - 1")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if algorithm == "midpoint" and workload_size > 2**52:
        raise ValueError("midpoint workload must not exceed 2^52 (float64 index resolution)")
    if method == "sequential" and process_count != 1:
        raise ValueError("sequential execution requires exactly one process")
    if process_count > cpu_limit() and not allow_oversubscribe:
        raise ValueError(f"process count exceeds {cpu_limit()} available logical CPUs")


def tasks(algorithm, workload, chunk_size, seed, rank=0, processes=1):
    source = (monte_carlo.iter_tasks(workload, chunk_size, seed, rank, processes)
              if algorithm == "monte_carlo" else
              midpoint_integration.iter_tasks(workload, chunk_size, rank, processes))
    for task in source:
        yield algorithm, task


def process_task(item):
    """Module-level worker, picklable with Windows spawn."""
    algorithm, task = item
    value, count = (monte_carlo.count_hits(task) if algorithm == "monte_carlo"
                    else midpoint_integration.integrate_chunk(task))
    return value, count, os.getpid()


def aggregate_partials(results, algorithm):
    processed, pids = 0, set()
    integer_total, total, correction = 0, 0.0, 0.0
    for value, count, pid in results:
        processed += count
        pids.add(pid)
        if algorithm == "monte_carlo":
            integer_total += int(value)
        else:
            updated = total + value
            correction += ((total - updated) + value if abs(total) >= abs(value)
                           else (value - updated) + total)
            total = updated
    return (integer_total if algorithm == "monte_carlo" else total + correction), processed, sorted(pids)


def make_result(algorithm, method, workload, processes, seed, chunk_size,
                total, processed, elapsed, worker_pids, working_pids):
    if processed != workload:
        raise RuntimeError(f"workload accounting mismatch: {processed} != {workload}")
    estimate = (4.0 * total / workload if algorithm == "monte_carlo" else total / workload)
    if not math.isfinite(estimate) or not 0 <= estimate <= 4:
        raise RuntimeError("invalid numerical estimate")
    hits = int(total) if algorithm == "monte_carlo" else None
    return dict(run_id=uuid4().hex, timestamp=datetime.now(timezone.utc).isoformat(),
                algorithm=algorithm, method=method, workload_size=workload,
                workload_unit=UNITS[algorithm], samples=workload, processes=processes,
                process_count=processes, seed=seed, random_seed=seed if algorithm == "monte_carlo" else None,
                chunk_size=chunk_size, hits=hits, inside_count=hits, processed_samples=processed,
                processed_units=processed, pi_estimate=estimate, absolute_error=abs(estimate - math.pi),
                compute_seconds=elapsed, execution_time=elapsed, timing_scope="compute_region",
                status="COMPLETED", error_message=None, worker_pids=worker_pids,
                working_pids=working_pids, world_size=processes if method == "mpi" else None)
