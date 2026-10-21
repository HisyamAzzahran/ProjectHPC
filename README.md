# HPC Parallel Computing & Performance Lab

**Judul penelitian:** Comparative Performance Analysis of Python Multiprocessing and MPI-Based Parallel Computing Using Monte Carlo and Numerical Integration Algorithms

Proyek mata kuliah **Scalable Parallel Program** untuk eksperimen scientific computing secara lokal di Windows x64. Dua algoritma estimasi π berjalan pada sequential, Python multiprocessing, dan MPI nyata. Dashboard Streamlit menyediakan delapan workspace, resource monitoring, benchmark interaktif, cancellation, serta riwayat berbasis berkas.

## Menjalankan dashboard

Dari PowerShell pada direktori proyek:

```powershell
cd 'D:\Project Kuliah\HPC-Monte-Carlo'
.\.venv\Scripts\python.exe launch_dashboard.py
```

Buka **http://localhost:8501**. Launcher membuka browser otomatis ketika server siap. Apabila `python` mengarah ke interpreter global, perintah berikut otomatis memilih `.venv` proyek jika tersedia:

```powershell
python launch_dashboard.py
```

Alternatif yang didukung:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run dashboard/app.py
# Tanpa pembukaan browser otomatis, atau dengan port lain:
python launch_dashboard.py --no-browser --port 8502
```

Aktivasi bukan keharusan; pemanggilan `.venv\Scripts\python.exe` langsung menghindari masalah execution policy. Tekan Ctrl+C untuk menghentikan server. Dashboard tidak menjalankan kalkulasi berat saat dibuka.

## Setup dari lingkungan bersih

Python 3.11+ 64-bit diperlukan; lingkungan yang diverifikasi memakai **3.11.9**. Python 3.12 dapat dipakai jika wheel dependensinya tersedia. Tidak diperlukan WSL, Docker, database, cloud, atau physical HPC cluster.

```powershell
# Hanya ketika .venv belum ada:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe environment.py
.\.venv\Scripts\python.exe -m pytest -q
```

`requirements.txt` mengunci dependensi langsung; `requirements-lock.txt` mencatat seluruh versi Windows yang digunakan. Untuk reproduksi environment dengan versi transitive yang sama:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Pilih `.venv\Scripts\python.exe` melalui **Python: Select Interpreter** di VS Code. Pengujian pytest sudah dikonfigurasi dalam workspace. Interpreter launcher `py` pada mesin ini tidak memiliki registrasi Python; perintah menggunakan `python` atau jalur venv eksplisit.

## Enam konfigurasi dan CLI

```powershell
.\.venv\Scripts\python.exe sequential.py --algorithm monte_carlo --workload 100000 --json
.\.venv\Scripts\python.exe multiprocessing_pi.py --algorithm monte_carlo --workload 100000 --processes 2 --json
& .\.venv\Library\bin\mpiexec.exe -n 2 .\.venv\Scripts\python.exe mpi_pi.py --algorithm monte_carlo --workload 100000 --json

.\.venv\Scripts\python.exe sequential.py --algorithm midpoint --workload 100000 --json
.\.venv\Scripts\python.exe multiprocessing_pi.py --algorithm midpoint --workload 100000 --processes 2 --json
& .\.venv\Library\bin\mpiexec.exe -n 2 .\.venv\Scripts\python.exe mpi_pi.py --algorithm midpoint --workload 100000 --json

& .\.venv\Library\bin\mpiexec.exe -n 2 .\.venv\Scripts\python.exe hello_mpi.py
```

Semua estimator mendukung `--algorithm`, `--workload`, `--chunk-size`, `--seed`, dan `--json`. Alias lama `--samples` tetap bekerja; algoritma default adalah Monte Carlo. Sequential hanya menerima satu proses. MPI mengambil process count dari `MPI.COMM_WORLD` melalui `mpiexec -n`, dan rank 0 saja mencetak hasil.

Workload Monte Carlo berarti **random samples**; workload Midpoint berarti **integration intervals**. N sama tidak menjamin jumlah operasi atau akurasi yang setara. Seed hanya digunakan Monte Carlo; field JSON `random_seed` bernilai null untuk Midpoint, sementara kolom legacy `seed` mempertahankan konfigurasi command.

Monte Carlo memakai PCG64 dan SeedSequence([master_seed, global_chunk_id]). Dengan N, seed, chunk size, dan versi NumPy sama, inside count identik lintas metode/process count. Midpoint memakai float64 dan Neumaier compensated summation untuk partial sums. Perbedaan kecil urutan MPI reduction diterima dalam toleransi numerik.

## Benchmark yang dapat direproduksi

Pilot kecil terlebih dahulu:

```powershell
.\.venv\Scripts\python.exe benchmark.py --algorithms monte_carlo midpoint --samples 100000 --processes 1 2 --repeats 3 --output results/dual_pilot.csv
```

Matriks penelitian yang telah dijalankan: dua algoritma, lima workload, p=1/2/4, tiga repetisi, **210 observasi pada 70 konfigurasi**:

```powershell
.\.venv\Scripts\python.exe benchmark.py --algorithms monte_carlo midpoint --samples 100000 500000 1000000 5000000 10000000 --processes 1 2 4 --repeats 3 --output results/dual_algorithm_benchmark.csv
.\.venv\Scripts\python.exe plot_results.py --input results/dual_algorithm_benchmark.csv --output-dir figures/dual_algorithm
.\.venv\Scripts\python.exe report_results.py --input results/dual_algorithm_benchmark.csv
```

`--warmups`, `--repeats`, `--chunk-size`, `--seed`, `--methods`, `--timeout`, dan `--mpiexec` dapat dikonfigurasi. Sequential harus disertakan sebagai baseline setiap algoritma. p=8 hanya layak dipilih jika hardware mendukung; mesin terdeteksi memiliki 6 physical cores/12 logical CPUs, sehingga matriks ini memakai p hingga 4. CLI menolak oversubscription tidak disengaja; override harus eksplisit dengan `--allow-oversubscribe`.

MPI-free benchmark tetap berfungsi:

```powershell
.\.venv\Scripts\python.exe benchmark.py --algorithms monte_carlo midpoint --methods sequential multiprocessing --samples 1000000 --processes 1 2 4 --repeats 3 --output results/no_mpi.csv
```

Runner menjalankan konfigurasi bergiliran dan mengacak urutannya secara deterministik per repetisi. Gunakan output berbeda untuk mempertahankan eksperimen sebelumnya. Dataset historis `results/benchmark.csv` dan `results/pilot.csv` tetap dipertahankan dan dibaca sebagai Monte Carlo.

## Definisi metrik

- **Primary E2E:** `perf_counter` di orchestrator mencakup launch, imports, registrasi proses, worker/rank startup, perhitungan, output, shutdown, dan cleanup. Monitoring diaktifkan secara konsisten.
- **Compute-region:** chunk evaluation dan agregasi; worker readiness/startup di luar region. MPI mencakup reductions numerik dan final barrier; pengumpulan statistik timing di luar region. Nilai ini diagnostik, terpisah dari speedup utama.
- **Speedup:** median sequential E2E **algoritma yang sama** / median E2E konfigurasi paralel pada N, seed, dan chunk yang sama.
- **Parallel efficiency:** speedup/p. CSV mengulang rasio median konfigurasi pada setiap baris repetisi.
- **CPU:** counter user+system CPU time dari proses milik job, termasuk final reading worker/rank, dibagi E2E dan jumlah logical CPU. Interval CPU peak/live tetap bersifat sampled.
- **Memory:** peak RSS yang teramati pada proses-proses job setiap 100 ms; shared pages dihitung per proses. Ini bukan unique physical memory atau peak kontinu yang dijamin.
- **Strong scaling:** total N tetap saat p berubah. Tidak ada klaim weak scaling atau multi-node scaling.

Rank Intel MPI yang tidak menjadi descendant langsung launcher diidentifikasi melalui registry privat dengan token job dan process creation time. Hal ini diperlukan untuk monitoring dan cancellation yang benar. Hasil awal dengan coverage launcher-only disimpan di `results/archive/` dan dikecualikan dari analisis final.

## Delapan workspace dashboard

| Workspace | Fitur |
|---|---|
| Overview | Hardware nyata, MPI status, latest benchmark, quick run, riwayat singkat |
| Simulation Lab | Kedua algoritma, ketiga metode, parameter, Run/Cancel/Reset, unduhan JSON |
| Algorithm Visualization | Scattergl sample-stream prefix Monte Carlo dan midpoint rectangles terpisah |
| Parallel Architecture | Aliran chunk/interval, worker/rank, aggregation, single-node topology |
| Performance Benchmarking | Konfigurasi matriks, Compare All Six, cancel, filter, delapan kategori grafik |
| Algorithm Comparison | Akurasi, E2E, scalability, RSS, observed error threshold |
| System Monitoring | System CPU/per-core/RAM, dashboard RSS, job process tree, histori |
| Experiment History | JSON/CSV persisten, filter/sort, details, logs, perbandingan run, download report |

Satu heavy job diizinkan per job manager/workspace melalui OS file lock. Komputasi berjalan dalam background thread yang mengelola subprocess; rendering Streamlit tidak menjalankan kernel panjang. Fragment UI refresh setiap 1–2 detik. Browser refresh dan navigasi tidak membuat salinan job.

Status: IDLE, STARTING, RUNNING, COMPLETED, FAILED, CANCELLED; pemulihan setelah server terputus menggunakan INTERRUPTED. Windows Job Object dan PID registry/psutil membersihkan proses milik job. Proses sangat singkat tetap memiliki keterbatasan sampling yang dijelaskan dalam laporan.

## Struktur dan hasil

```text
algorithms/                  Monte Carlo adapter dan Midpoint kernel
core/                        numeric execution, subprocess engine, monitoring,
                             PID registry, job manager, atomic persistence
dashboard/                   app, views, components, Plotly charts, CSS
sequential.py                sequential untuk kedua algoritma
multiprocessing_pi.py        Windows spawn workers
mpi_pi.py                    real MPI ranks dan collective reductions
benchmark.py                 raw CSV, medians, metadata
plot_results.py              PNG 300 DPI; kompatibel dengan CSV lama
report_results.py            laporan pengukuran berbahasa Indonesia
launch_dashboard.py          satu perintah untuk server dan browser
tests/                       pytest + pengujian regresi unittest lama
results/dual_algorithm_*      matriks final, summary, metadata
results/jobs/<run_id>/        job.json, result.json, logs, resources.csv;
                             benchmark job juga memiliki CSV/report/figures
figures/dual_algorithm/       37 grafik penelitian final
docs/                        proposal, teknis, hasil, validasi
```

Pembukaan dashboard tidak menampilkan pengukuran performa palsu. Educational visualization dibedakan dari hasil penuh. Grafik log error hanya menampilkan error positif; error nol float64 tetap tersedia dalam tabel dan bukan bukti integral dihitung eksak.

## Troubleshooting

```powershell
Test-Path .\.venv\Library\bin\mpiexec.exe
.\.venv\Scripts\python.exe -c "from mpi4py import MPI; print(MPI.Get_library_version())"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe launch_dashboard.py --no-browser --port 8502
```

Gunakan launcher/runtime dan interpreter venv yang sama. Jika MPI tidak tersedia, dashboard menonaktifkan pemilihannya dan dua metode lainnya tetap berjalan. Tidak ada perubahan PATH global, registry, firewall, atau execution policy. Matplotlib cache berada di `.cache/matplotlib`. Untuk kebijakan keamanan kampus yang memblokir MPI, simpan stderr asli dan minta administrator memeriksa runtime terkait.

## Dokumentasi

- [Proposal penelitian](docs/project_proposal.md)
- [Dokumentasi teknis](docs/technical_documentation.md)
- [Hasil dan pembahasan aktual](docs/results_and_discussion.md)
- [Validasi peningkatan proyek](docs/upgrade_validation.md)
- [Catatan validasi proyek Monte Carlo awal](docs/validation.md)

Referensi primer: [Python multiprocessing](https://docs.python.org/3.11/library/multiprocessing.html), [NumPy parallel random generation](https://numpy.org/doc/stable/reference/random/parallel.html), [mpi4py installation](https://mpi4py.readthedocs.io/en/stable/install.html), [Streamlit fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment), [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest), [psutil](https://psutil.readthedocs.io/).

