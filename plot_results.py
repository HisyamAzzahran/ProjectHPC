"""Scientific PNG exports from real legacy or dual-algorithm measurements."""
import argparse
import os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".cache" / "matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from benchmark import GROUP_KEYS, normalize_data, summarize
from environment import ROOT

COLORS = {"sequential": "#555B6E", "multiprocessing": "#0072B2", "mpi": "#D55E00"}
LABELS = {"monte_carlo": "Monte Carlo", "midpoint": "Midpoint Integration"}


def load_results(path):
    data = normalize_data(pd.read_csv(path))
    required = ["method", "samples", "processes", "seed", "chunk_size", "repetition",
                "processed_samples", "pi_estimate", "absolute_error", "end_to_end_seconds", "compute_seconds", "hits"]
    missing = set(required) - set(data)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")
    if data.empty or data[[c for c in required if c != "hits"]].isna().any().any():
        raise ValueError("CSV is empty or incomplete")
    if not set(data.method) <= set(COLORS) or not set(data.algorithm) <= set(LABELS):
        raise ValueError("Unknown method or algorithm")
    if (data[["end_to_end_seconds", "compute_seconds", "samples", "processes"]] <= 0).any().any():
        raise ValueError("Timings and sizes must be positive")
    if data.duplicated(GROUP_KEYS + ["repetition"]).any():
        raise ValueError("Duplicate benchmark observations")
    if not data.processed_samples.eq(data.samples).all():
        raise ValueError("Workload accounting mismatch")
    for algorithm, subset in data.groupby("algorithm"):
        if len(subset[["seed", "chunk_size"]].drop_duplicates()) != 1:
            raise ValueError("Plot one seed/chunk configuration per algorithm")
        for _, current in subset.groupby("samples"):
            if algorithm == "monte_carlo" and (current.hits.isna().any() or current.hits.nunique() != 1):
                raise ValueError("Monte Carlo hit counts disagree")
            if algorithm == "midpoint" and current.pi_estimate.max() - current.pi_estimate.min() > 1e-12:
                raise ValueError("Midpoint estimates disagree")
    return data


def generate_plots(input_path, output_dir, cancel_event=None):
    summary = summarize(load_results(input_path))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.22})
    created = []
    multiple = summary.algorithm.nunique() > 1

    def save(fig, name):
        if cancel_event is not None and cancel_event.is_set():
            plt.close(fig)
            from core.simulation_engine import ExecutionCancelled
            raise ExecutionCancelled("cancelled during figure export")
        fig.tight_layout()
        path = output_dir / name
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        created.append(path)

    for algorithm, algorithm_data in summary.groupby("algorithm"):
        prefix = algorithm + "_" if multiple or algorithm != "monte_carlo" else ""
        for n, current in algorithm_data.groupby("samples"):
            ticks = sorted(current.processes.unique())
            for metric, ylabel, name in (
                ("median_end_to_end_seconds", "Median end-to-end time (s)", "execution_time"),
                ("speedup", "Speedup (algorithm-specific E2E baseline)", "speedup"),
                ("parallel_efficiency", "Parallel efficiency", "efficiency")):
                fig, ax = plt.subplots(figsize=(7.2, 4.7))
                baseline = current[current.method == "sequential"].iloc[0]
                ax.axhline(baseline[metric], linestyle="--", color=COLORS["sequential"], label="Sequential baseline")
                for method in ("multiprocessing", "mpi"):
                    rows = current[current.method == method].sort_values("processes")
                    if rows.empty:
                        continue
                    errors = None
                    if name == "execution_time":
                        errors = np.vstack([rows[metric] - rows.min_end_to_end_seconds,
                                            rows.max_end_to_end_seconds - rows[metric]])
                    ax.errorbar(rows.processes, rows[metric], yerr=errors, marker="o", capsize=3,
                                color=COLORS[method], label=method)
                if name == "speedup":
                    ax.plot(ticks, ticks, ":", color="#009E73", label="Ideal linear speedup")
                ax.set(xlabel="Number of processes", ylabel=ylabel, xticks=ticks,
                       title=f"{LABELS[algorithm]}: N={n:,}")
                ax.set_ylim(bottom=0)
                ax.legend(fontsize=9)
                save(fig, f"{prefix}{name}_{n}.png")
        fig, ax = plt.subplots(figsize=(7.2, 4.7))
        for (method, p), rows in algorithm_data.groupby(["method", "processes"]):
            rows = rows.sort_values("samples")
            ax.plot(rows.samples, rows.median_end_to_end_seconds, "o-", label=f"{method}, p={p}")
        ax.set(xlabel="Workload size", ylabel="Median end-to-end time (s)", xscale="log", yscale="log",
               title=f"{LABELS[algorithm]}: workload comparison")
        ax.legend(fontsize=8)
        save(fig, prefix + "workload_comparison.png")
        fig, ax = plt.subplots(figsize=(7.2, 4.7))
        rows = algorithm_data[algorithm_data.method == "sequential"].sort_values("samples")
        ax.plot(rows.samples, rows.absolute_error, "o-", color="#0072B2", label="Measured absolute error")
        ax.set(xlabel="Workload size", ylabel="Absolute error |estimate - pi|", xscale="log",
               title=f"{LABELS[algorithm]}: estimation error")
        ax.set_ylim(bottom=0)
        ax.legend()
        save(fig, prefix + "estimation_error.png")
    if multiple:
        for metric, label, name in (
            ("median_end_to_end_seconds", "Median end-to-end time (s)", "algorithm_comparison"),
            ("median_peak_rss_mb", "Sampled peak tree RSS (MiB; shared pages counted per process)", "memory_comparison"),
            ("median_cpu_mean_percent", "Mean CPU (% of total logical system capacity)", "cpu_comparison")):
            if metric not in summary:
                continue
            fig, ax = plt.subplots(figsize=(8, 5))
            for (algorithm, method), rows in summary.groupby(["algorithm", "method"]):
                rows = rows[rows.processes == rows.processes.max()].sort_values("samples")
                ax.plot(rows.samples, rows[metric], "o-", label=f"{LABELS[algorithm]}, {method}, p={int(rows.iloc[0].processes)}")
            ax.set(xlabel="Workload size", ylabel=label, xscale="log", title=label.split(" (")[0])
            ax.legend(fontsize=8)
            save(fig, name + ".png")
    return created


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results" / "benchmark.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
    args = parser.parse_args()
    try:
        paths = generate_plots(args.input, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Cannot plot measured results: {exc}\n")
    print(f"Saved {len(paths)} measured figures at 300 DPI: {args.output_dir}")


if __name__ == "__main__":
    main()

