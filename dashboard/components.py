"""Shared measured state and responsive job panel."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from benchmark import normalize_data, summarize
from core.execution_manager import get_manager
from environment import ROOT, inspect_environment

ALGORITHM_NAMES = {"monte_carlo": "Monte Carlo Simulation", "midpoint": "Midpoint Numerical Integration"}
METHOD_NAMES = {"sequential": "Sequential", "multiprocessing": "Multiprocessing", "mpi": "MPI"}


@st.cache_data(ttl=600, show_spinner=False)
def environment_info():
    return inspect_environment()


def mpi_available():
    info = environment_info()
    return bool(info.get("mpi_launcher") and not info.get("mpi_error"))


def methods():
    return ["sequential", "multiprocessing", "mpi"] if mpi_available() else ["sequential", "multiprocessing"]


def benchmark_files():
    candidates = list((ROOT / "results").glob("*.csv"))
    candidates += list((ROOT / "results" / "jobs").glob("*/benchmark.csv"))
    files = []
    for path in candidates:
        if path.name.endswith("_summary.csv"):
            continue
        metadata = path.with_suffix(".metadata.json")
        try:
            if json.loads(metadata.read_text(encoding="utf-8")).get("status") == "complete":
                files.append(path)
        except (OSError, ValueError):
            continue
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


@st.cache_data(show_spinner=False)
def read_benchmark(path, modified):
    from plot_results import load_results
    return load_results(path)


def dataset_selector(key):
    files = benchmark_files()
    if not files:
        st.info("No completed benchmark data yet. Run an experiment to create measured charts.")
        return None
    default_index = next((index for index, path in enumerate(files) if path.name == "dual_algorithm_benchmark.csv"), 0)
    selected = st.selectbox("Measured dataset", files, index=default_index, key=key,
                            format_func=lambda p: str(p.relative_to(ROOT)))
    return read_benchmark(str(selected), selected.stat().st_mtime_ns)


def result_metrics(result):
    columns = st.columns(4)
    columns[0].metric("Estimated π", f"{result['pi_estimate']:.12f}")
    columns[1].metric("Absolute error", f"{result['absolute_error']:.3e}")
    columns[2].metric("End-to-end", f"{result['end_to_end_seconds']:.4f} s")
    columns[3].metric("Compute region", f"{result['compute_seconds']:.4f} s")


@st.fragment(run_every="1s")
def job_panel():
    manager = get_manager()
    record = manager.current()
    if not record:
        return
    active = record["status"] in {"STARTING", "RUNNING"}
    with st.container(border=True):
        title, action = st.columns([5, 1])
        title.markdown(f"**{record['kind'].title()} · {record['status']}** · `{record['run_id'][:10]}`")
        if active and action.button("Cancel job", key="global_cancel"):
            manager.cancel()
            st.rerun(scope="fragment")
        config = record["config"]
        title.caption(f"{config.get('algorithm', ', '.join(config.get('algorithms', [])))} · "
                      f"{config.get('method', 'benchmark matrix')} · process count: {config.get('process_count', config.get('processes'))}")
        if active:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(record["timestamp"])).total_seconds()
            c = st.columns(4)
            c[0].metric("Elapsed", f"{elapsed:.1f} s")
            resources = record.get("resources", {})
            c[1].metric("Job tree CPU / system capacity", f"{resources['app_cpu_percent']:.1f}%" if resources else "—")
            c[2].metric("Job tree RSS", f"{resources['app_rss_mb']:.1f} MiB" if resources else "—")
            c[3].metric("Observed tree processes", resources.get("tree_process_count", "—"))
            st.caption("Running in a background subprocess. Elapsed time is live; no unsupported percentage progress is inferred.")
        elif record["status"] == "COMPLETED":
            result = record.get("result") or {}
            if record["kind"] == "simulation":
                result_metrics(result)
                st.caption(f"Processed {result['processed_units']:,} {result['workload_unit']}; "
                           f"{len(result['worker_pids'])} computational processes initialized.")
                st.download_button("Download result JSON", json.dumps(result, indent=2),
                                   file_name=f"{record['run_id']}.json", mime="application/json", key="global_result_download")
            else:
                st.success("Benchmark complete. Measured CSV, figures, and report are available in Experiment History.")
        else:
            st.warning(record.get("error_message") or record["status"])
