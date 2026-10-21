"""Deterministic, memory-bounded Monte Carlo kernel shared by every method."""

import argparse
import json
import math
import os
from collections.abc import Iterator

import numpy as np


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number <= 0 or number > 2**63 - 1:
        raise argparse.ArgumentTypeError("must be between 1 and 2^63 - 1")
    return number


def nonnegative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return number


def available_cpu_ids() -> set[int]:
    """Logical CPUs in this process's affinity mask (single processor group)."""
    if hasattr(os, "sched_getaffinity"):
        return set(os.sched_getaffinity(0))
    if os.name == "nt":
        import ctypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
        if kernel.GetProcessAffinityMask(
            ctypes.c_void_p(kernel.GetCurrentProcess()),
            ctypes.byref(process_mask), ctypes.byref(system_mask)
        ):
            return {i for i in range(process_mask.value.bit_length()) if process_mask.value & (1 << i)}
    return set(range(os.cpu_count() or 1))


def cpu_limit() -> int:
    """Available logical CPUs; respect affinity when the OS exposes it."""
    return len(available_cpu_ids())


def validate_processes(parser, processes: int, allow_oversubscribe: bool) -> None:
    if processes > cpu_limit() and not allow_oversubscribe:
        parser.error(
            f"{processes} processes exceed {cpu_limit()} available logical CPUs; "
            "use --allow-oversubscribe to opt in"
        )


def common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--algorithm", choices=["monte_carlo", "midpoint"], default="monte_carlo")
    parser.add_argument("--workload", "--samples", dest="samples", type=positive_int, default=1_000_000)
    parser.add_argument("--seed", type=nonnegative_int, default=2026)
    parser.add_argument("--chunk-size", type=positive_int, default=100_000)
    parser.add_argument("--json", action="store_true", help="emit exactly one JSON result")
    return parser


def iter_tasks(samples: int, chunk_size: int, seed: int,
               rank: int = 0, processes: int = 1) -> Iterator[tuple[int, int, int]]:
    """Yield (chunk index, point count, seed), with cyclic disjoint ownership."""
    if samples <= 0 or chunk_size <= 0 or seed < 0:
        raise ValueError("samples and chunk_size must be positive; seed nonnegative")
    if processes <= 0 or not 0 <= rank < processes:
        raise ValueError("invalid rank or process count")
    chunks = (samples + chunk_size - 1) // chunk_size
    for index in range(rank, chunks, processes):
        yield index, min(chunk_size, samples - index * chunk_size), seed


def count_hits(task: tuple[int, int, int]) -> tuple[int, int]:
    """PCG64 stream keyed by (root seed, global chunk index), never worker ID."""
    index, points, seed = task
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, index])))
    xy = rng.random((points, 2))
    np.square(xy, out=xy)
    hits = np.count_nonzero(xy[:, 0] + xy[:, 1] <= 1.0)
    return int(hits), points


def aggregate(results) -> tuple[int, int]:
    hits = samples = 0
    for chunk_hits, chunk_samples in results:
        hits += chunk_hits
        samples += chunk_samples
    return hits, samples


def make_result(method: str, samples: int, processes: int, seed: int,
                chunk_size: int, hits: int, processed: int, compute_seconds: float) -> dict:
    if processed != samples or not 0 <= hits <= samples:
        raise RuntimeError(f"invalid aggregation: requested={samples}, processed={processed}, hits={hits}")
    estimate = 4.0 * hits / samples
    return dict(method=method, samples=samples, processes=processes, seed=seed,
                chunk_size=chunk_size, hits=hits, processed_samples=processed,
                pi_estimate=estimate, absolute_error=abs(estimate - math.pi),
                compute_seconds=compute_seconds)


def print_result(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, allow_nan=False), flush=True)
    else:
        print(f"Algorithm: {result.get('algorithm', 'monte_carlo')} | Method: {result['method']} | Workload: {result['samples']:,} | Processes: {result['processes']}")
        print(f"Estimated pi: {result['pi_estimate']:.10f} | Absolute error: {result['absolute_error']:.10f}")
        if result.get("algorithm") == "midpoint":
            print(f"Processed integration intervals: {result['processed_samples']:,}")
        else:
            print(f"Hits: {result['hits']:,} | Processed samples: {result['processed_samples']:,}")
        print(f"Compute region: {result['compute_seconds']:.6f} s")

