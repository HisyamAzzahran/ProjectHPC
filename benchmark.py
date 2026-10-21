"""Scientific benchmarking of both algorithms using independent sequential baselines."""
import argparse
import csv
import json
import math
import random
from pathlib import Path
import pandas as pd

from environment import ROOT, find_mpiexec, inspect_environment
from monte_carlo import nonnegative_int, positive_int, validate_processes
from core.simulation_engine import child_environment, run_simulation
from core.workload_manager import ALGORITHMS, METHODS

RAW_COLUMNS = ["run_id", "timestamp", "algorithm", "workload_unit", "method", "samples", "processes",
               "seed", "chunk_size", "repetition", "hits", "processed_samples", "pi_estimate",
               "absolute_error", "end_to_end_seconds", "compute_seconds", "cpu_mean_percent",
               "cpu_peak_percent", "peak_rss_mb", "monitoring_samples", "speedup", "parallel_efficiency"]
GROUP_KEYS = ["algorithm", "method", "samples", "processes", "seed", "chunk_size"]


def normalize_data(data):
    data = data.copy()
    if "algorithm" not in data:
        data["algorithm"] = "monte_carlo"
    if "workload_unit" not in data:
        data["workload_unit"] = data.algorithm.map({"monte_carlo": "random samples", "midpoint": "integration intervals"})
    return data


def summarize(data):
    data = normalize_data(data)
    aggregations = dict(runs=("repetition", "count"),
        median_end_to_end_seconds=("end_to_end_seconds", "median"),
        min_end_to_end_seconds=("end_to_end_seconds", "min"),
        max_end_to_end_seconds=("end_to_end_seconds", "max"),
        median_compute_seconds=("compute_seconds", "median"),
        pi_estimate=("pi_estimate", "first"), absolute_error=("absolute_error", "first"), hits=("hits", "first"))
    for column in ("cpu_mean_percent", "cpu_peak_percent", "peak_rss_mb"):
        if column in data:
            aggregations["median_" + column] = (column, "median")
    grouped = data.groupby(GROUP_KEYS, as_index=False).agg(**aggregations)
    baseline_keys = ["algorithm", "samples", "seed", "chunk_size"]
    baseline = grouped[grouped.method == "sequential"][
        baseline_keys + ["median_end_to_end_seconds"]
    ].rename(columns={"median_end_to_end_seconds": "baseline_end_to_end_seconds"})
    grouped = grouped.merge(baseline, on=baseline_keys, validate="many_to_one")
    if len(grouped) != len(data[GROUP_KEYS].drop_duplicates()):
        raise ValueError("a sequential baseline is required for every algorithm/workload/seed/chunk size")
    grouped["speedup"] = grouped.baseline_end_to_end_seconds / grouped.median_end_to_end_seconds
    grouped["parallel_efficiency"] = grouped.speedup / grouped.processes
    return grouped


def run_one(method, samples, processes, chunk_size, seed, launcher=None, timeout=120,
            allow_oversubscribe=False, algorithm="monte_carlo"):
    return run_simulation(algorithm, method, samples, processes, seed, chunk_size,
                          launcher, timeout, allow_oversubscribe)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithms", "--algorithm", nargs="+", choices=ALGORITHMS, default=["monte_carlo"])
    parser.add_argument("--workloads", "--workload", "--samples", dest="samples", type=positive_int,
                        nargs="+", default=[100_000, 500_000, 1_000_000, 5_000_000])
    parser.add_argument("--processes", type=positive_int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--warmups", type=nonnegative_int, default=0)
    parser.add_argument("--seed", type=nonnegative_int, default=2026)
    parser.add_argument("--chunk-size", type=positive_int, default=100_000)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--mpiexec")
    parser.add_argument("--timeout", type=positive_int, default=120)
    parser.add_argument("--allow-oversubscribe", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "benchmark.csv")
    args = parser.parse_args()
    if "sequential" not in args.methods:
        parser.error("--methods must include sequential for each algorithm's baseline")
    for processes in args.processes:
        validate_processes(parser, processes, args.allow_oversubscribe)
    if "midpoint" in args.algorithms and max(args.samples) > 2**52:
        parser.error("midpoint workload must not exceed 2^52")
    try:
        launcher = find_mpiexec(args.mpiexec) if "mpi" in args.methods else None
    except FileNotFoundError as exc:
        parser.error(str(exc))
    if "mpi" in args.methods and not launcher:
        parser.error("MPI unavailable; select --methods sequential multiprocessing")
    configs = [(algorithm, method, samples, processes)
               for algorithm in dict.fromkeys(args.algorithms)
               for samples in dict.fromkeys(args.samples)
               for method in dict.fromkeys(args.methods)
               for processes in ([1] if method == "sequential" else dict.fromkeys(args.processes))]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = inspect_environment()
    metadata["benchmark_arguments"] = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    metadata.update(selected_mpi_launcher=launcher, status="running",
                    monitoring="100 ms psutil snapshots plus token/birth-verified rank registry and final worker CPU readings; mean CPU=accounted CPU seconds/E2E/logical CPUs; RSS sums shared pages",
                    timing="perf_counter: launch through termination/cleanup; monitoring enabled consistently in all methods",
                    child_thread_environment={k: v for k, v in child_environment().items() if k.endswith("NUM_THREADS")})
    metadata_path = args.output.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    results, expected = [], {}
    schedule = random.Random(args.seed)
    try:
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RAW_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for repetition in range(1 - args.warmups, args.repeats + 1):
                order = configs.copy()
                schedule.shuffle(order)
                for algorithm, method, samples, processes in order:
                    print(f"{algorithm}/{method}: N={samples:,}, p={processes}, round={repetition}", flush=True)
                    row = run_one(method, samples, processes, args.chunk_size, args.seed, launcher,
                                  args.timeout, args.allow_oversubscribe, algorithm)
                    key = (algorithm, samples)
                    numerical = row["hits"] if algorithm == "monte_carlo" else row["pi_estimate"]
                    previous = expected.setdefault(key, numerical)
                    agrees = numerical == previous if algorithm == "monte_carlo" else math.isclose(numerical, previous, abs_tol=1e-13, rel_tol=1e-14)
                    if not agrees:
                        raise RuntimeError(f"Cross-model numerical mismatch for {key}")
                    if repetition > 0:
                        row.update(repetition=repetition, speedup="", parallel_efficiency="")
                        results.append({k: row.get(k) for k in RAW_COLUMNS})
                        writer.writerow(row)
                        handle.flush()
    except BaseException as exc:
        metadata.update(status="failed", error=str(exc))
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        raise
    data = pd.DataFrame(results)
    summary = summarize(data)
    data = data.drop(columns=["speedup", "parallel_efficiency"]).merge(
        summary[GROUP_KEYS + ["speedup", "parallel_efficiency"]], on=GROUP_KEYS, validate="many_to_one")
    data[RAW_COLUMNS].to_csv(args.output, index=False)
    summary_path = args.output.with_name(args.output.stem + "_summary.csv")
    summary.to_csv(summary_path, index=False)
    metadata.update(status="complete", measured_runs=len(data), warmup_runs=len(configs) * args.warmups)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved {len(data)} actual measurements to {args.output}", flush=True)


if __name__ == "__main__":
    main()
