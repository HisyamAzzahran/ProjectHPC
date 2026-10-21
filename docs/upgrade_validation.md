# Catatan Validasi Peningkatan Proyek

Verifikasi dilakukan pada **20 Oktober 2026, Asia/Jakarta**. Metadata eksperimen menyimpan timestamp UTC. Semua angka di bawah berasal dari eksekusi nyata; pengujian tidak dianggap lulus sebelum command selesai sukses.

## Komponen awal yang diperiksa

Source Monte Carlo, sequential/multiprocessing/MPI entry points, benchmark, Matplotlib plots, report generator, environment inventory, sembilan tests lama, requirements, venv, starter ZIP, dan hasil sebelumnya diperiksa. Sembilan pengujian awal dijalankan ulang sebelum penambahan algoritma dan lulus dalam 15.039 s.

Python yang digunakan adalah 3.11.9 x64. CPU terdeteksi Intel Core i7-10750H, 6 physical cores/12 logical CPUs; OS-reported RAM 31.77 GiB. Intel MPI 2021.18.1 dan mpi4py 4.1.2 tersedia dalam venv. Interpreter Python tidak di-upgrade hanya untuk mengejar preferensi 3.12 karena environment lama berfungsi.

Dataset Monte Carlo awal `results/benchmark.csv`, `results/pilot.csv`, summary/metadata, serta starter ZIP tetap dipertahankan. Algoritma random lama tidak diubah stream-nya: konfigurasi default N=100,000 tetap menghasilkan 78,676 hits dan pi=3.14704.

## Phase gate backend

Sebelum dashboard dibuat, 19 pengujian backend lulus dalam 4.20 s. Midpoint memakai float64 fixed chunks, independent scalar reference, interval coverage tepat satu kali, dan compensated aggregation. Monte Carlo mempertahankan global chunk seed. Keenam kombinasi diuji melalui subprocess nyata.

| Algoritma | Sequential | Multiprocessing | MPI |
|---|---|---|---|
| Monte Carlo | Lulus | Lulus; worker PID diverifikasi | Lulus; world size/rank PID diverifikasi |
| Midpoint | Lulus | Lulus; worker PID diverifikasi | Lulus; float SUM reduction diverifikasi |

Contoh Midpoint N=100,003, chunk=997, p=2 memberikan pi=3.141592653598126 dan absolute error sekitar 8.33289e-12 pada ketiga model. Semua processed count tepat sama dengan workload.

## Perbaikan yang ditemukan selama verifikasi

1. Intel MPI meluncurkan rank yang tidak seluruhnya tampak pada direct launcher process tree. Monitoring diperbaiki dengan registry token dan process creation time, registrasi sebelum import NumPy, serta OS CPU counters pada completion. Cancellation rank terlepas diuji secara langsung.
2. Windows dapat menolak replace file registry yang sedang dibaca monitor. Registry kini memakai immutable snapshots; persisted job JSON memakai retry singkat untuk atomic replace. Pengujian benchmark job yang sempat gagal kemudian lulus.
3. Validasi numerical result diperbaiki agar Monte Carlo dengan zero hits pada workload sangat kecil tetap sah.
4. Formatter CLI diperbaiki agar Midpoint tanpa `--json` menampilkan processed intervals dan tidak memformat inside count yang tidak berlaku. Keenam human-readable CLI variants diuji.

Matriks dan pilot awal dengan coverage launcher-only disimpan di `results/archive/` dengan metadata `archived_partial_resource_coverage`. Berkas tersebut dikecualikan dari analisis final dan pemilih dataset dashboard. Benchmark final dan pilot dijalankan ulang menggunakan monitoring yang diperbaiki.

## Dependensi dan reproducibility

Dependensi scientific/MPI awal dipertahankan. Ditambahkan Streamlit 1.66.0, Plotly 7.1.0, psutil 7.2.2, dan pytest 9.1.1. Pillow menggunakan 12.3.0 untuk memenuhi batas kompatibilitas Streamlit. Dependensi langsung terdapat pada `requirements.txt`; semua versi lingkungan Windows direkam dalam `requirements-lock.txt`.

Pemasangan ke `.venv` dan `.venv-repro` berhasil. Upaya jaringan awal dalam sandbox ditolak; pemasangan diteruskan dengan akses jaringan yang disetujui. Kedua environment melaporkan `No broken requirements found` pada `pip check`. Tidak ada pemasangan global, perubahan PATH, registry, firewall, atau execution policy.

## Pengujian akhir

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Hasil suite final: **53 passed, 18 subtests passed in 74.54s**, tanpa failures atau skips.

Lingkungan terisolasi kedua menjalankan full suite yang saat itu berisi **44 tests dan 18 subtests**, semuanya lulus dalam 66.76 s. Setelah penambahan launcher/CLI cases, **9 pengujian tambahan** juga lulus dalam 10.02 s. Dengan demikian 53 cases yang sama telah diverifikasi di environment kedua, melalui dua invocation.

Cakupan pengujian:

- Dua algoritma pada sequential, spawn workers, dan real MPI ranks.
- Deterministic Monte Carlo equality, seed berbeda, zero-hit boundary, dan legacy stream.
- Midpoint convergence dan independent scalar reference.
- Interval/chunk coverage tanpa overlap/missing, workload tidak habis dibagi p, idle workers/ranks.
- Initialized PID/world-size checks dan pembersihan processes setelah selesai.
- Invalid CLI/API input, command failure, timeout, cancellation multiprocessing dan MPI.
- MPI resource coverage yang mencakup rank terdaftar.
- Job exclusion melalui file lock, durable CSV/JSON, interrupted-owner recovery, error persistence.
- Benchmark nyata dua algoritma, baseline per algoritma, CSV schema, warm-up exclusion, median ratios.
- PNG generation dan report generation dari hasil nyata.
- Delapan halaman Streamlit AppTest, kedua visualisasi, actual UI simulation submission.
- Run/Cancel/Reset, navigasi/rerun tanpa duplicate job, Compare All Six yang menjalankan benchmark nyata.
- Launcher via interpreter venv dan Python global, HTTP health/HTML, serta invalid port.

Source compilation berhasil dan konfigurasi VS Code pytest valid. Tidak tersedia browser automation tool pada sesi ini; UI diuji dengan AppTest, bukan pixel-level browser inspection. Pembukaan browser otomatis diimplementasikan, sedangkan smoke server menggunakan `--no-browser` agar pengujian tidak mengganggu desktop.

## Benchmark dan grafik final

```powershell
.\.venv\Scripts\python.exe benchmark.py --algorithms monte_carlo midpoint --samples 100000 --processes 1 2 --repeats 3 --output results/dual_pilot.csv
.\.venv\Scripts\python.exe benchmark.py --algorithms monte_carlo midpoint --samples 100000 500000 1000000 5000000 10000000 --processes 1 2 4 --repeats 3 --output results/dual_algorithm_benchmark.csv
.\.venv\Scripts\python.exe plot_results.py --input results/dual_algorithm_benchmark.csv --output-dir figures/dual_algorithm
.\.venv\Scripts\python.exe report_results.py --input results/dual_algorithm_benchmark.csv
```

| Artefak | Verifikasi aktual |
|---|---|
| `results/dual_pilot.csv` | 30 measured runs, dua algoritma, p=1/2 |
| `results/dual_algorithm_benchmark.csv` | 210 measured rows, 70 configurations, tiga repetisi masing-masing |
| `results/dual_algorithm_benchmark_summary.csv` | 70 median-based summaries |
| `results/dual_algorithm_benchmark.metadata.json` | Complete; versi/hardware/arguments/monitoring dicatat |
| `figures/dual_algorithm/` | 37 PNG; DPI metadata sekitar 299.9994, representasi PNG untuk 300 DPI |
| `docs/results_and_discussion.md` | Laporan Indonesia dari actual final CSV |

Pemeriksaan independen mengonfirmasi processed_samples=N pada seluruh 210 baris, exact Monte Carlo hit equality, toleransi Midpoint, tiga repetisi per konfigurasi, E2E>compute time, CPU counters positif, serta MPI RSS coverage di atas launcher-only footprint. Grafis tidak menggunakan smoothing atau synthetic performance values.

Tidak ada dari 60 konfigurasi paralel final yang mempunyai median E2E speedup>1. Hal ini membatasi kesimpulan pada workload/perangkat ini. Compute-region improvements tidak dipromosikan menjadi E2E speedup. Nilai, rentang, akurasi, dan keterbatasan lengkap tersedia pada laporan hasil.

## Dashboard dan persistent history

Delapan workspace telah diimplementasikan: Overview, Simulation Lab, Algorithm Visualization, Parallel Architecture, Performance Benchmarking, Algorithm Comparison, System Monitoring, dan Experiment History. Job manager memakai real subprocesses, satu heavy job, file-based records, live logs, dan resource samples. Job tidak diluncurkan ulang oleh Streamlit rerun.

Dua eksekusi integrasi nyata disimpan sebagai contoh riwayat, dengan tujuan verifikasi dicatat dalam metadata:

- Monte Carlo multiprocessing, N=100,003, p=2, chunk=997: run `7edd528cc007466fa1ba97f69861dd1e`.
- Midpoint MPI, N=100,003, p=2, chunk=997: run `d9693d84f5a64287955a8d4bc96d1a51`.

Lokasi: `results/jobs/<run_id>/`. Ini adalah hasil komputasi nyata dari job manager, bukan dummy history. Test-only jobs memakai temporary directories dan tidak dimasukkan ke riwayat riset.

## Launcher dan status akhir

```powershell
python launch_dashboard.py
# Atau interpreter eksplisit:
.\.venv\Scripts\python.exe launch_dashboard.py
```

URL default adalah **http://localhost:8501**. Launcher `--no-browser` benar-benar dijalankan; endpoint `/_stcore/health` mengembalikan HTTP 200 `ok`, dan halaman HTML mengembalikan HTTP 200. Pengujian launcher juga memverifikasi port alternatif dan cleanup owned server processes. Server smoke dihentikan setelah pemeriksaan; menjalankan launcher kembali membuka aplikasi.

Tidak ada blocker konfigurasi yang mencegah penggunaan. MPI tersedia dan diuji nyata. Sampling CPU/RSS memiliki batas resolusi yang dinyatakan dalam dokumentasi; cluster multi-node, weak scaling, dan pixel-level browser QA tidak diuji atau diklaim.
