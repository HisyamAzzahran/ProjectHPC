"""Generate Indonesian scientific discussion from real algorithm-specific baselines."""
import argparse
import json
from pathlib import Path
from benchmark import summarize
from environment import ROOT
from plot_results import load_results


def generate_report(input_path, output_path):
    input_path, output_path = Path(input_path), Path(output_path)
    data = load_results(input_path)
    summary = summarize(data).sort_values(["algorithm", "samples", "method", "processes"])
    metadata = json.loads(input_path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "complete":
        raise ValueError("benchmark must have complete status")
    hardware = metadata.get("hardware", {})
    lines = ["# Hasil dan Pembahasan", "",
             "Laporan ini dibangkitkan dari pengukuran aktual. Waktu dapat berubah ketika eksperimen diulang.", "",
             "## Konfigurasi eksperimen", "",
             f"- Sumber: `{input_path.name}`; timestamp UTC: {metadata['timestamp_utc']}.",
             f"- CPU: {hardware.get('cpu_name', 'tidak terdeteksi')}; physical cores: {hardware.get('physical_cores')}; logical CPUs: {metadata.get('logical_cpus')}.",
             f"- Python: {metadata['python'].splitlines()[0]}.",
             f"- MPI: {metadata.get('mpi_library', metadata.get('mpi_error', 'tidak tersedia'))}.",
             f"- Platform yang dilaporkan OS: {metadata['platform']}.",
             f"- measured observations: {len(data)}; warm-up yang dibuang: {metadata.get('warmup_runs', 0)}.",
             f"- Repetisi per konfigurasi: {int(summary.runs.min())} sampai {int(summary.runs.max())}.",
             "- Monitoring: process-tree psutil setiap 100 ms pada eksperimen baru; overhead monitoring termasuk E2E.",
             "- CPU dinormalisasi terhadap kapasitas seluruh logical CPU; RSS dijumlahkan per proses, sehingga shared pages dapat dihitung berulang.",
             "- Mean CPU memakai OS user+system counters termasuk completion readings, dibagi E2E dan logical CPU count. Registry token/creation-time mencakup rank MPI yang terlepas dari launcher tree.",
             "", "## Results tables", "",
             "Speedup menggunakan median sequential algoritma yang sama pada N, seed, dan chunk size yang sama. Compute-region tidak dicampur dengan timer E2E.",
             "", "| Algoritma | N | Metode | p | Median E2E (s) | Min-max E2E (s) | Compute (s) | Speedup | Efficiency |",
             "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for r in summary.itertuples():
        lines.append(f"| {r.algorithm} | {r.samples:,} | {r.method} | {r.processes} | {r.median_end_to_end_seconds:.6f} | {r.min_end_to_end_seconds:.6f}-{r.max_end_to_end_seconds:.6f} | {r.median_compute_seconds:.6f} | {r.speedup:.4f} | {r.parallel_efficiency:.4f} |")
    lines += ["", "Min-max adalah rentang observasi, bukan confidence interval.", "",
              "## Akurasi numerik", "", "| Algoritma | N | Estimasi pi | Absolute error |", "|---|---:|---:|---:|"]
    for r in summary[summary.method == "sequential"].itertuples():
        lines.append(f"| {r.algorithm} | {r.samples:,} | {r.pi_estimate:.16f} | {r.absolute_error:.6e} |")
    lines += ["", "Monte Carlo diverifikasi dengan inside-count integer yang sama persis; Midpoint diverifikasi dengan toleransi float64. Semua processed count sama dengan N. Seed tidak digunakan oleh Midpoint.", "",
              "## Execution time, speedup, dan parallel efficiency", ""]
    for algorithm, current in summary.groupby("algorithm"):
        lines += [f"### {algorithm}", ""]
        for n, rows in current.groupby("samples"):
            fastest = rows.loc[rows.median_end_to_end_seconds.idxmin()]
            parallel = rows[rows.method != "sequential"]
            lines.append(f"Pada N={n:,}, median E2E terendah adalah {fastest.method} (p={int(fastest.processes)}): {fastest.median_end_to_end_seconds:.6f} s.")
            if not parallel.empty:
                lines.append(f"Speedup paralel berada pada {parallel.speedup.min():.4f}-{parallel.speedup.max():.4f}; efficiency {parallel.parallel_efficiency.min():.4f}-{parallel.parallel_efficiency.max():.4f}.")
        lines.append("")
    lines += ["## Konsumsi sumber daya", ""]
    if "median_peak_rss_mb" in summary:
        lines += ["| Algoritma | Metode | p | N | Median sampled peak RSS (MiB) | Median mean CPU (%) |",
                  "|---|---|---:|---:|---:|---:|"]
        for r in summary.itertuples():
            lines.append(f"| {r.algorithm} | {r.method} | {r.processes} | {r.samples:,} | {r.median_peak_rss_mb:.2f} | {r.median_cpu_mean_percent:.2f} |")
    else:
        lines += ["Data lama tidak memiliki pengukuran CPU/RSS; nilai tersebut tidak direkonstruksi."]
    lines += ["", "## Strong scaling dan Amdahl's Law", "",
              "Setiap kurva strong scaling mempertahankan N tetap dan mengubah p. Idealnya S(p)=p dan E(p)=1. Amdahl's Law klasik adalah S(p)=1/[s+(1-s)/p]. Peluncuran interpreter, import NumPy, spawn, dispatch, IPC, dan MPI collective menambah biaya yang tidak dimodelkan oleh fraksi serial tetap.",
              "Perbedaan E2E dan compute-region mencakup beberapa komponen tersebut sekaligus; selisihnya bukan pengukuran komunikasi murni. Data ini tidak cukup untuk mengidentifikasi atau memfit fraksi serial secara andal.",
              "Satu chunk hanya dapat dikerjakan satu worker/rank. Karena itu N=100,000 dengan chunk size=100,000 tidak menyediakan concurrency komputasi, walaupun proses tambahan benar-benar diluncurkan. Chunk yang tidak habis dibagi p menimbulkan load imbalance.", "",
              "## Perbandingan kedua algoritma", "",
              "N adalah jumlah random samples untuk Monte Carlo dan jumlah integration intervals untuk Midpoint. N sama tidak berarti jumlah operasi, kebutuhan random generation, atau target akurasi sama. Monte Carlo memiliki error stokastik dengan expected standard deviation O(N^-1/2). Midpoint untuk integrand mulus memiliki truncation error O(N^-2), hingga keterbatasan floating-point mendominasi. Error nol terhadap math.pi berarti kesamaan representasi float64, bukan bukti solusi eksak.",
              "Repetisi benchmark memakai seed yang sama untuk memisahkan variasi waktu dari variasi sampel. Repetisi tersebut bukan independent statistical replications. Tidak ada klaim algoritma yang selalu lebih baik atau interpolasi time-to-accuracy di luar pengukuran.", "",
              "## Keterbatasan", "",
              "- Satu workstation, local single-node, tanpa multi-node network, weak scaling, atau cluster fisik.",
              "- Tiga repetisi default memberikan median/rentang deskriptif, bukan signifikansi statistik.",
              "- Suhu, power plan, CPU frequency, aplikasi latar belakang, dan MPI affinity tidak dikontrol.",
              "- Peak RSS dan CPU bersifat sampled; proses sangat singkat dapat terlewat dan shared pages tidak dideduplikasi.",
              "- Pengukuran baru dengan monitoring tidak digabung dengan baseline historis tanpa monitoring.",
              "- Waktu render Plotly/Matplotlib dan pembuatan laporan di luar timer benchmark setiap konfigurasi.", "",
              "## Kesimpulan", ""]
    for algorithm, current in summary.groupby("algorithm"):
        parallel = current[current.method != "sequential"]
        if not parallel.empty:
            count = int((parallel.speedup > 1).sum())
            lines.append(f"Untuk {algorithm}, {count} dari {len(parallel)} konfigurasi paralel memiliki median E2E speedup >1. Kesimpulan dibatasi pada matriks dan perangkat ini.")
    lines += ["", "Reproduksi menggunakan README. CSV mentah dan metadata adalah bukti utama; grafik dan tabel berasal dari berkas tersebut.", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results" / "dual_algorithm_benchmark.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "results_and_discussion.md")
    args = parser.parse_args()
    try:
        path = generate_report(args.input, args.output)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Cannot generate report: {exc}\n")
    print(f"Saved measured report: {path}")


if __name__ == "__main__":
    main()

