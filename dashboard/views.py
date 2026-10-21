"""Eight dashboard workspaces, backed by numerical services and persisted evidence."""
import math
from datetime import datetime, timezone
from html import escape
import pandas as pd
import plotly.express as px
import streamlit as st

from benchmark import summarize
from core.execution_manager import get_manager
from core.system_monitor import system_snapshot
from environment import ROOT
from monte_carlo import cpu_limit
from dashboard.charts import COLORS, midpoint_figure, monte_carlo_figure, polish, scaling_chart
from dashboard.components import (ALGORITHM_NAMES, METHOD_NAMES, benchmark_files, dataset_selector,
                                  environment_info, methods, mpi_available, read_benchmark)


def chart(figure, key):
    st.plotly_chart(figure, width="stretch", theme=None, key=key,
                    config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 3}})


def overview():
    info = environment_info()
    manager = get_manager()
    history = manager.store.history()
    hardware = info.get("hardware", {})
    st.markdown('<div class="hero"><div class="eyebrow">HPC PARALLEL COMPUTING & PERFORMANCE LAB</div>'
                '<h2>Explore parallel performance.</h2><p>Two numerical algorithms. Three execution models. '
                'A local laboratory for reproducible experiments, numerical accuracy, and strong scaling.</p>'
                '<br><span class="pill">LOCAL · SINGLE NODE</span><span class="pill pill-muted">SCALABLE PARALLEL PROGRAM</span></div>',
                unsafe_allow_html=True)
    c = st.columns(4)
    c[0].metric("Physical / logical cores", f"{hardware.get('physical_cores', '—')} / {info['logical_cpus']}")
    ram = hardware.get("ram_bytes")
    c[1].metric("OS-reported RAM", f"{ram / 2**30:.1f} GiB" if ram else "—")
    c[2].metric("Completed interactive jobs", sum(r["status"] == "COMPLETED" for r in history))
    c[3].metric("Execution status", "RUNNING" if manager.busy() else "IDLE")
    st.write("")
    left, right = st.columns([1.4, 1])
    with left, st.container(border=True):
        st.subheader("Workstation")
        st.write(hardware.get("cpu_name", "CPU name unavailable"))
        st.caption(f"Python {info['python'].split()[0]} · {info['architecture']} · {cpu_limit()} available logical CPUs")
        st.write("MPI runtime: " + (info.get("mpi_library", "Unavailable") if mpi_available() else "Unavailable"))
        st.caption("All workers and ranks execute on this computer. No physical cluster is implied.")
    with right, st.container(border=True):
        st.subheader("Quick start")
        st.write("Run 1,000,000 Monte Carlo samples with two local workers.")
        if st.button("Run quick simulation", type="primary", disabled=manager.busy(), key="quick_run"):
            try:
                manager.start_simulation(algorithm="monte_carlo", method="multiprocessing", workload_size=1_000_000,
                                         process_count=min(2, cpu_limit()), seed=2026, chunk_size=100_000)
                st.rerun()
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
        st.caption("The run is real and its result is saved to local history.")
    completed = [r for r in history if r["status"] == "COMPLETED" and r["kind"] == "simulation"]
    if completed:
        latest = completed[0]["result"]
        c = st.columns(2)
        c[0].metric("Latest simulation E2E", f"{latest['end_to_end_seconds']:.4f} s")
        c[1].metric("Latest estimated π", f"{latest['pi_estimate']:.12f}")
    st.subheader("Latest measured benchmark")
    files = benchmark_files()
    if files:
        path = files[0]
        data = read_benchmark(str(path), path.stat().st_mtime_ns)
        st.caption(f"{len(data)} actual observations · {path.relative_to(ROOT)}")
        st.dataframe(summarize(data)[["algorithm", "method", "samples", "processes", "median_end_to_end_seconds", "speedup"]].tail(8),
                     hide_index=True, width="stretch")
    else:
        st.info("No benchmark measurements yet. Use Performance Benchmarking to begin.")
    st.subheader("Recent experiment history")
    frame = manager.store.export_frame()
    if frame.empty:
        st.caption("No interactive jobs have been submitted yet. Existing research CSVs remain available above.")
    else:
        available = [c for c in ["timestamp", "kind", "algorithm", "method", "status", "elapsed_seconds"] if c in frame]
        st.dataframe(frame[available].head(5), hide_index=True, width="stretch")


def reset_simulation():
    st.session_state.update(sim_algorithm="monte_carlo", sim_method="sequential", sim_workload=1_000_000,
                            sim_chunk=100_000, sim_seed=2026, sim_processes_sequential=1,
                            sim_processes_multiprocessing=min(2, cpu_limit()), sim_processes_mpi=min(2, cpu_limit()))


def simulation():
    manager = get_manager()
    left, right = st.columns([1.15, 1])
    with left:
        algorithm = st.selectbox("Algorithm", list(ALGORITHM_NAMES), format_func=ALGORITHM_NAMES.get, key="sim_algorithm")
        method = st.selectbox("Execution method", methods(), format_func=METHOD_NAMES.get, key="sim_method")
        if not mpi_available():
            st.info("MPI is unavailable. Sequential and Multiprocessing remain ready.")
        unit = "random samples" if algorithm == "monte_carlo" else "integration intervals"
        with st.form("simulation_configuration"):
            workload = st.number_input(f"Workload size ({unit})", min_value=1, max_value=1_000_000_000,
                                       value=1_000_000, step=100_000, key="sim_workload")
            process_count = st.number_input("Computational processes", min_value=1, max_value=cpu_limit(),
                                            value=1 if method == "sequential" else min(2, cpu_limit()),
                                            disabled=method == "sequential", key=f"sim_processes_{method}")
            chunk_size = st.number_input("Chunk size", min_value=1, max_value=2_000_000,
                                         value=100_000, step=1000, key="sim_chunk")
            seed = (st.number_input("Master random seed", min_value=0, max_value=2**32-1,
                                    value=2026, step=1, key="sim_seed") if algorithm == "monte_carlo" else 0)
            submitted = st.form_submit_button("Run Simulation", type="primary", disabled=manager.busy())
        st.button("Reset Configuration", on_click=reset_simulation)
        if submitted:
            try:
                manager.start_simulation(algorithm=algorithm, method=method, workload_size=int(workload),
                                         process_count=1 if method == "sequential" else int(process_count),
                                         seed=int(seed), chunk_size=int(chunk_size))
                st.rerun()
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
    with right, st.container(border=True):
        st.subheader(ALGORITHM_NAMES[algorithm])
        if algorithm == "monte_carlo":
            st.latex(r"\hat\pi=4\frac{H}{N},\quad x^2+y^2\leq 1")
            st.write("Sample the unit square, count points inside the quarter circle, and reduce integer hit counts.")
            st.caption("Global chunk identity determines each random stream. Matching seed, workload, and chunk size produce identical inside counts across methods.")
        else:
            st.latex(r"\pi=\int_0^1\frac{4}{1+x^2}dx\approx\frac{1}{N}\sum_{i=0}^{N-1}\frac{4}{1+((i+0.5)/N)^2}")
            st.write("Partition [0,1] into equal intervals and sum the integrand at their midpoints using float64 arithmetic.")
            st.caption("Seed is not applicable. Compensated chunk summation reduces rounding error; reduction order may still cause small differences.")
        st.divider()
        st.write("**Expected result**")
        st.write("Estimated π, absolute error, exact processed workload count, end-to-end time, compute-region time, and sampled CPU/RSS.")
        st.caption("The live job panel below provides cancellation and result download. It continues updating as you navigate.")


def visualization():
    algorithm = st.selectbox("Visualized algorithm", list(ALGORITHM_NAMES), format_func=ALGORITHM_NAMES.get, key="viz_algorithm")
    record = get_manager().current()
    result = record.get("result") if record and record["kind"] == "simulation" and record["status"] == "COMPLETED" else None
    if algorithm == "monte_carlo":
        seed = st.number_input("Visualization master seed", min_value=0, value=2026, step=1, key="viz_seed")
        if result and result["algorithm"] == algorithm:
            workload, chunk, seed = result["workload_size"], result["chunk_size"], result["seed"]
            st.caption("Displaying the actual deterministic sample-stream prefix of the latest completed simulation.")
        else:
            workload, chunk = 100_000, 100_000
            st.caption("Educational stream preview only. Run a simulation for a full computed result.")
        figure, displayed, hits = monte_carlo_figure(workload, int(seed), chunk)
        c = st.columns(3)
        c[0].metric("Displayed points", f"{displayed:,}")
        c[1].metric("Inside displayed subset", f"{100*hits/displayed:.2f}%")
        c[2].metric("Subset π estimate", f"{4*hits/displayed:.6f}")
        chart(figure, "monte_carlo_domain")
        st.caption(f"Only {displayed:,} points displayed; requested full workload: {workload:,}. Subset statistics are not the full benchmark result.")
    else:
        rectangles = st.slider("Educational rectangle count", min_value=4, max_value=120, value=20)
        figure, area = midpoint_figure(rectangles)
        c = st.columns(2)
        c[0].metric("Illustrated area / π estimate", f"{area:.10f}")
        c[1].metric("Illustrated absolute error", f"{abs(area-math.pi):.3e}")
        chart(figure, "midpoint_domain")
        st.caption("These rectangles are an independent educational calculation, not the millions of intervals in a benchmark. Each rectangle has width 1/N and height f((i+0.5)/N).")
    if result and result["algorithm"] == algorithm:
        st.success(f"Latest full result: π={result['pi_estimate']:.14f} · error={result['absolute_error']:.3e} · "
                   f"{result['processed_units']:,} {result['workload_unit']}")


def architecture():
    record = get_manager().current()
    active = bool(record and record["status"] in {"STARTING", "RUNNING"} and record["kind"] == "simulation")
    config = record["config"] if active else {}
    if active:
        st.info(f"Active simulation: {config['algorithm']} · {config['method']} · {config['process_count']} computational processes")
        algorithm, method, count = config["algorithm"], config["method"], config["process_count"]
    else:
        st.caption("Configured topology preview. This diagram does not claim workers are currently running.")
        c = st.columns(3)
        algorithm = c[0].selectbox("Topology algorithm", list(ALGORITHM_NAMES), format_func=ALGORITHM_NAMES.get)
        method = c[1].selectbox("Topology execution model", methods(), format_func=METHOD_NAMES.get)
        count = 1 if method == "sequential" else c[2].number_input("Preview processes", 1, cpu_limit(), min(4, cpu_limit()))
    partition = "Deterministic random sample chunks" if algorithm == "monte_carlo" else "Disjoint integration interval chunks"
    aggregation = "Integer inside-count SUM" if algorithm == "monte_carlo" else "Float64 partial-sum aggregation"
    steps = [("Input workload", "N samples" if algorithm == "monte_carlo" else "N equal integration intervals"),
             ("Partition workload", partition), (METHOD_NAMES[method], f"{count} local computational process(es)"),
             ("Partial results", "Counts and processed units" if algorithm == "monte_carlo" else "Integrand sums and processed intervals"),
             ("Aggregation", aggregation), ("Final estimate", "π, error, timing, and accounting checks")]
    html = '<div class="flow">'
    for i, (title, detail) in enumerate(steps, 1):
        html += f'<div class="flow-card"><span class="flow-number">0{i}</span><strong>{escape(title)}</strong><small>{escape(detail)}</small></div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)
    columns = st.columns(min(int(count), 4))
    for index in range(int(count)):
        label = f"MPI rank {index}" if method == "mpi" else (f"Local worker {index+1}" if method == "multiprocessing" else "Main process")
        columns[index % len(columns)].markdown(f'<div class="worker"><strong>{label}</strong><div class="muted">{escape(partition)}</div></div>', unsafe_allow_html=True)
    if method == "mpi":
        st.write("Ranks use cyclic global chunk ownership and MPI.SUM reductions. Rank 0 emits the structured result; MPI.MAX selects the longest compute-region duration.")
    elif method == "multiprocessing":
        st.write("A parent process launches spawn workers, dispatches chunks, and collects partial results over local IPC. The parent is included in E2E overhead.")
    else:
        st.write("One process evaluates all chunks directly. This is the algorithm-specific sequential baseline.")
    st.caption("Single-node parallel computing: all processes share this workstation's CPU and memory resources.")


def benchmarking():
    manager = get_manager()
    with st.expander("Configure a real benchmark", expanded=True):
        c = st.columns(2)
        algorithms = c[0].multiselect("Benchmark algorithms", list(ALGORITHM_NAMES), default=list(ALGORITHM_NAMES), format_func=ALGORITHM_NAMES.get)
        selected_methods = c[1].multiselect("Benchmark methods", methods(), default=methods(), format_func=METHOD_NAMES.get)
        workloads = c[0].multiselect("Workload sizes", [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000],
                                    default=[100_000, 1_000_000], format_func=lambda n: f"{n:,}")
        hardware = environment_info().get("hardware", {})
        allowed = sorted({n for n in [1, 2, 4, hardware.get("physical_cores", 1)] if n and n <= cpu_limit()})
        if (hardware.get("physical_cores") or 0) >= 8 and cpu_limit() >= 8:
            allowed = sorted(set(allowed + [8]))
        processes = c[1].multiselect("Parallel process counts", allowed, default=[n for n in [1, 2, 4] if n in allowed])
        extra = c[0].text_input("Additional workloads (comma-separated)", placeholder="e.g. 250000, 2000000")
        repeats = c[1].number_input("Measured repetitions", min_value=1, max_value=20, value=3)
        seed = c[0].number_input("Benchmark Monte Carlo seed", min_value=0, value=2026, step=1)
        chunk = c[1].number_input("Benchmark chunk size", min_value=1, max_value=2_000_000, value=100_000, step=1000)
        st.caption("Sequential is measured once per algorithm/workload in each repetition. Configurations execute one at a time. Speedup always uses that algorithm's own sequential baseline.")
        c = st.columns(2)
        run = c[0].button("Run Benchmark", type="primary", disabled=manager.busy())
        compare = c[1].button("Compare All Six Configurations" if mpi_available() else "Compare available configurations", disabled=manager.busy())
        if run or compare:
            try:
                extra_values = [int(item.strip()) for item in extra.split(",") if item.strip()]
                if any(not 0 < n <= 1_000_000_000 for n in extra_values):
                    raise ValueError("additional workloads must be between 1 and 1,000,000,000")
                manager.start_benchmark(algorithms=list(ALGORITHM_NAMES) if compare else algorithms,
                                        methods=methods() if compare else selected_methods,
                                        workloads=sorted(set(workloads + extra_values)), processes=processes,
                                        repeats=int(repeats), seed=int(seed), chunk_size=int(chunk))
                st.rerun()
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
    st.subheader("Measured performance analytics")
    data = dataset_selector("benchmark_dataset")
    if data is None:
        return
    c = st.columns(3)
    algorithm = c[0].selectbox("Chart algorithm", sorted(data.algorithm.unique()), format_func=ALGORITHM_NAMES.get)
    chart_methods = c[1].multiselect("Chart methods", sorted(data.method.unique()), default=sorted(data.method.unique()))
    workload = c[2].selectbox("Fixed workload for strong scaling", sorted(data.samples.unique()), format_func=lambda n: f"{n:,}")
    summary = summarize(data)
    chosen = summary[(summary.algorithm == algorithm) & (summary.method.isin(chart_methods)) & (summary.samples == workload)]
    if chosen.empty:
        st.info("Select at least one measured method.")
        return
    scaling, accuracy, resources = st.tabs(["Strong scaling", "Algorithms & accuracy", "CPU & memory"])
    with scaling:
        chart(scaling_chart(chosen, "median_end_to_end_seconds", "Execution time vs processes · fixed N"), "benchmark_time")
        c = st.columns(2)
        with c[0]:
            chart(scaling_chart(chosen, "speedup", "End-to-end speedup"), "benchmark_speedup")
        with c[1]:
            chart(scaling_chart(chosen, "parallel_efficiency", "Parallel efficiency"), "benchmark_efficiency")
        chart(scaling_chart(chosen, "median_compute_seconds", "Compute-region strong scaling (s) · diagnostic"), "benchmark_compute")
        st.caption("The ideal line assumes zero launch and coordination overhead. Compute-region timings remain separate from the primary E2E speedups.")
    with accuracy:
        matched = summary[(summary.samples == workload) & summary.method.isin(chart_methods)]
        chart(polish(px.bar(matched, x="algorithm", y="median_end_to_end_seconds", color="method", barmode="group",
                             facet_col="processes", color_discrete_map=COLORS), "Performance by algorithm · same N, different numerical work"), "benchmark_algorithm")
        chart(polish(px.bar(matched, x="method", y="median_end_to_end_seconds", color="algorithm", barmode="group",
                             facet_col="processes"), "Performance by execution method"), "benchmark_method")
        error = summary[summary.method == "sequential"]
        positive = error[error.absolute_error > 0]
        chart(polish(px.line(positive, x="samples", y="absolute_error", color="algorithm", markers=True,
                              log_x=True, log_y=True), "Measured absolute error vs workload size"), "benchmark_error")
        st.caption("Log scale shows positive errors only; exact float64 matches with math.pi remain visible in the table. Equal N does not imply equal accuracy or operation counts.")
    with resources:
        if "median_peak_rss_mb" not in chosen:
            st.info("This historical dataset did not measure CPU/RSS. Select a new benchmark dataset.")
        else:
            c = st.columns(2)
            with c[0]:
                chart(scaling_chart(chosen, "median_cpu_mean_percent", "Mean process-tree CPU (% system capacity)"), "benchmark_cpu")
            with c[1]:
                chart(scaling_chart(chosen, "median_peak_rss_mb", "Sampled peak process-tree RSS (MiB)"), "benchmark_memory")
            st.caption("Sampling interval: 100 ms. Short-lived processes can be missed; summed RSS includes shared pages once per process.")
    st.dataframe(summary, hide_index=True, width="stretch")
    st.download_button("Export measured CSV", data.to_csv(index=False), "measured_benchmark.csv", "text/csv")


def comparison():
    st.caption("Numerical accuracy and parallel performance answer different research questions.")
    st.dataframe(pd.DataFrame({
        "Dimension": ["Mathematical problem", "Behavior", "Workload unit", "Expected error", "Parallel partition", "Aggregation"],
        "Monte Carlo": ["Area of quarter unit circle", "Stochastic, seeded", "Random (x,y) samples", "Standard deviation O(N^-1/2)", "Globally seeded chunks", "Exact integer hit-count SUM"],
        "Midpoint": ["Integral of 4/(1+x²) over [0,1]", "Deterministic, float64", "Equal integration intervals", "Truncation O(N^-2) for smooth integrand", "Disjoint interval chunks", "Compensated partial sums + float64 reduction"]
    }), hide_index=True, width="stretch")
    data = dataset_selector("comparison_dataset")
    if data is None:
        return
    if data.algorithm.nunique() < 2:
        st.info("This dataset contains one algorithm. Select a completed dual-algorithm experiment for measured comparisons.")
        return
    summary = summarize(data)
    method = st.selectbox("Comparison execution method", sorted(summary.method.unique()))
    available = sorted(summary[summary.method == method].processes.unique())
    count = st.selectbox("Matched process count", available)
    chosen = summary[(summary.method == method) & (summary.processes == count)]
    c = st.columns(2)
    with c[0]:
        chart(polish(px.line(chosen, x="samples", y="median_end_to_end_seconds", color="algorithm", markers=True,
                              log_x=True), "Measured execution time (s)"), "comparison_time")
    with c[1]:
        positive = chosen[chosen.absolute_error > 0]
        chart(polish(px.line(positive, x="samples", y="absolute_error", color="algorithm", markers=True,
                              log_x=True, log_y=True), "Numerical accuracy · positive errors"), "comparison_accuracy")
    if "median_peak_rss_mb" in chosen:
        c = st.columns(2)
        with c[0]:
            chart(polish(px.line(chosen, x="samples", y="median_peak_rss_mb", color="algorithm", markers=True, log_x=True), "Sampled peak tree RSS (MiB)"), "comparison_rss")
        with c[1]:
            chart(polish(px.line(chosen, x="samples", y="speedup", color="algorithm", markers=True, log_x=True), "Algorithm-specific E2E speedup"), "comparison_scalability")
    threshold = st.number_input("Absolute error threshold (observed runs only)", min_value=1e-15, max_value=1.0,
                                value=0.001, format="%.8g")
    successful = chosen[chosen.absolute_error <= threshold]
    if successful.empty:
        st.info("No measured configuration in this selection meets the threshold.")
    else:
        evidence = successful.loc[successful.groupby("algorithm").median_end_to_end_seconds.idxmin()]
        st.dataframe(evidence[["algorithm", "samples", "processes", "absolute_error", "median_end_to_end_seconds"]], hide_index=True)
        st.caption("Fastest qualifying observation among measured workloads only. This is not an estimated stopping time, an error guarantee, or evidence about untested N or independent seeds.")
    st.dataframe(chosen, hide_index=True, width="stretch")


@st.fragment(run_every="2s")
def monitoring():
    snapshot = system_snapshot()
    row = dict(timestamp=datetime.now(timezone.utc).isoformat(), system_cpu_percent=snapshot["cpu_percent"],
               system_memory_percent=snapshot["memory_percent"], dashboard_rss_mb=snapshot["application_rss_mb"])
    history = st.session_state.setdefault("monitor_history", [])
    history.append(row)
    del history[:-180]
    st.caption("Live operating-system measurements. System-wide values are separate from this dashboard and the selected computational job.")
    c = st.columns(4)
    c[0].metric("System CPU", f"{snapshot['cpu_percent']:.1f}%")
    c[1].metric("System memory", f"{snapshot['memory_percent']:.1f}%")
    c[2].metric("Dashboard process RSS", f"{snapshot['application_rss_mb']:.1f} MiB")
    c[3].metric("Logical processors", snapshot["logical_cpus"])
    cores = pd.DataFrame({"Logical CPU": [str(i) for i in range(len(snapshot["per_cpu_percent"]))],
                          "Utilization (%)": snapshot["per_cpu_percent"]})
    chart(polish(px.bar(cores, x="Logical CPU", y="Utilization (%)", color_discrete_sequence=["#48B8EA"]),
                 "CPU utilization per logical processor"), "monitor_per_cpu")
    chart(polish(px.line(pd.DataFrame(history), x="timestamp", y=["system_cpu_percent", "system_memory_percent"]),
                 "System monitoring history (%)"), "monitor_system_history")
    record = get_manager().current()
    if record:
        st.subheader("Selected HPC execution")
        st.write(f"{record['status']} · {record['kind']} · {record['run_id']}")
        c = st.columns(3)
        resource = record.get("resources") or {}
        c[0].metric("Latest observed job-tree processes", resource.get("tree_process_count", "—"))
        c[1].metric("Latest job-tree RSS", f"{resource['app_rss_mb']:.1f} MiB" if resource else "—")
        c[2].metric("Recorded job duration", f"{record.get('elapsed_seconds', 0):.1f} s")
        st.caption("Tree counts include launcher/controller/helper processes. Computational worker/rank counts are recorded separately in completed simulation results.")
        tree = record.get("process_tree", [])
        if tree:
            st.dataframe(pd.DataFrame(tree), hide_index=True, width="stretch")
        path = get_manager().store.job_dir(record["run_id"]) / "resources.csv"
        if path.exists() and path.stat().st_size:
            try:
                resources = pd.read_csv(path).tail(180)
                chart(polish(px.line(resources, x="elapsed_seconds", y="app_rss_mb"), "Job-tree sampled RSS (MiB)"), "monitor_job_rss")
            except (pd.errors.EmptyDataError, pd.errors.ParserError):
                st.caption("Waiting for a complete monitoring row.")
    else:
        st.info("Submit a simulation or benchmark to inspect its process tree and resources.")


def history():
    manager = get_manager()
    records = manager.store.history()
    frame = manager.store.export_frame()
    if frame.empty:
        st.info("No interactive experiments yet. Run a simulation or benchmark to create persistent history.")
        return
    c = st.columns(3)
    statuses = c[0].multiselect("History status", sorted(frame.status.unique()), default=sorted(frame.status.unique()))
    kinds = c[1].multiselect("Experiment type", sorted(frame.kind.unique()), default=sorted(frame.kind.unique()))
    if "algorithm" not in frame:
        frame["algorithm"] = "benchmark matrix"
    frame["algorithm"] = frame.algorithm.fillna("benchmark matrix")
    algorithms = c[2].multiselect("History algorithm", sorted(frame.algorithm.unique()), default=sorted(frame.algorithm.unique()))
    filtered = frame[frame.status.isin(statuses) & frame.kind.isin(kinds) & frame.algorithm.isin(algorithms)]
    columns = [c for c in ["run_id", "timestamp", "algorithm", "method", "workload_size", "process_count",
                           "pi_estimate", "absolute_error", "end_to_end_seconds", "status", "kind"] if c in filtered]
    st.dataframe(filtered[columns], hide_index=True, width="stretch")
    st.caption("Click column headers to sort. Records survive browser refresh and application restarts; interrupted jobs never appear completed.")
    st.download_button("Export history CSV", filtered.to_csv(index=False), "experiment_history.csv", "text/csv")
    if filtered.empty:
        return
    selected = st.selectbox("Run details", filtered.run_id.tolist())
    record = next(record for record in records if record["run_id"] == selected)
    directory = manager.store.job_dir(selected)
    with st.expander("Structured run metadata", expanded=True):
        st.json(record)
    c = st.columns(2)
    for column, name in zip(c, ["stdout.log", "stderr.log"]):
        with column:
            st.write(f"**{name}**")
            path = directory / name
            st.code(path.read_text(encoding="utf-8")[-16000:] if path.exists() else "No captured log available yet.", language="text")
    for name, label, mime in [("benchmark.csv", "Download benchmark CSV", "text/csv"),
                              ("report.md", "Download benchmark report", "text/markdown"),
                              ("result.json", "Download run result", "application/json"),
                              ("resources.csv", "Download resource history", "text/csv")]:
        path = directory / name
        if path.exists():
            st.download_button(label, path.read_bytes(), file_name=f"{selected}_{name}", mime=mime, key=f"history_{name}")
    compare_ids = st.multiselect("Compare historical simulations", [r["run_id"] for r in records if r["kind"] == "simulation" and r["status"] == "COMPLETED"])
    if compare_ids:
        rows = [r["result"] for r in records if r["run_id"] in compare_ids]
        table = pd.DataFrame(rows)
        chart(polish(px.bar(table, x="run_id", y="end_to_end_seconds", color="algorithm",
                            hover_data=["method", "workload_size", "process_count"]), "Selected historical runs · E2E seconds"), "history_comparison")
