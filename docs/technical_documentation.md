# Dokumentasi Teknis

## Environment dan setup

Target lokal adalah Windows x64 dengan Python 3.11+. Lingkungan aktual memakai Python 3.11.9, Intel Core i7-10750H, 6 physical cores, 12 logical CPUs, dan OS-reported RAM sekitar 31.77 GiB. Label Windows API/registry yang bersifat legacy dicatat apa adanya bersama build 26300, tanpa mengasumsikan edition dari target spesifikasi.

Dependensi scientific dan MPI awal dipertahankan. Streamlit, Plotly, psutil, dan pytest ditambahkan dalam venv; Pillow menggunakan 12.3.0 untuk memenuhi batas Streamlit <13. Tidak diperlukan perubahan sistem global. Perintah lengkap berada pada [README](../README.md). `requirements-lock.txt` merekam seluruh dependensi Windows yang diuji.

Intel MPI wheel menyediakan `.venv/Library/bin/mpiexec.exe`. `environment.py` mendeteksi launcher venv sebelum PATH dan memeriksa MPI library melalui child interpreter, agar controller tidak menginisialisasi MPI.

## Algoritma Monte Carlo

Untuk N titik uniform (x,y) pada [0,1)^2, hit H memenuhi x²+y²≤1 dan estimasi adalah 4H/N. Absolute error dihitung terhadap math.pi. Chunk i berisi min(chunk_size, N-i*chunk_size) titik dengan PCG64(SeedSequence([seed,i])). Semua model menjalankan chunk yang sama, sehingga scheduling dan p tidak mengubah inside count.

Array float64 berukuran (m,2) dikuadratkan in-place; memory utama kernel sekitar 25m bytes pada puncak temporary array, di luar library/process overhead. Chunk size mengontrol memory per worker. Mengubah chunk size dapat mengubah sample stream dan harus dicatat untuk reproduksi.

Di bawah independent sampling ideal, standard deviation estimator berorde N^-1/2. Repetisi dengan seed sama mengukur variasi waktu, bukan distribusi statistical error. Tidak ada klaim independensi formal semua pseudorandom streams.

## Algoritma Midpoint integration

Identitas yang digunakan adalah π=∫₀¹4/(1+x²)dx. Interval i memiliki titik tengah (i+0.5)/N; hasil akhir adalah Σf(midpoint)/N. Kernel memakai np.arange float64 per chunk, operasi in-place, dan np.sum(dtype=float64). Partial sums digabung menggunakan Neumaier compensated summation dalam sequential/parent/per-rank. MPI memakai SUM pada partial float64 rank.

Chunk menyimpan global start/count/N, sehingga interval tidak digeser akibat p atau pembagian yang tidak habis. Setiap interval dievaluasi tepat satu kali. Batas N≤2^52 menjaga resolusi indeks setengah pada float64; dashboard membatasi input default ke workload praktis ≤1 miliar dan chunk ≤2 juta unit. CLI dapat dikonfigurasi di luar batas UI dengan batas numerik tersebut.

Midpoint memiliki truncation error O(N^-2) untuk integrand mulus sebelum floating-point rounding mendominasi. Estimasi yang sama dengan math.pi tidak membuktikan integral eksak. Perbedaan urutan reduction diterima dengan toleransi, berbeda dari equality integer yang diwajibkan Monte Carlo.

## Workload distribution dan model eksekusi

`core/workload_manager.py` menyediakan dispatch kernel, task generator, validation, agregasi, serta standardized results. `sequential.py`, `multiprocessing_pi.py`, dan `mpi_pi.py` tetap menjadi entry point lama. Alias --samples dipertahankan untuk --workload dan default algoritma tetap Monte Carlo.

Sequential mengolah seluruh chunk pada satu process. Compute timer mencakup task iteration dan agregasi; startup, result construction, dan output berada di luar region.

Multiprocessing menggunakan explicit spawn, module-level worker, main guard, dan freeze_support. Queue mencatat PID worker yang telah diinisialisasi; dua barrier memisahkan readiness dari compute region. Parent mendistribusikan chunk dengan imap_unordered(chunksize=1). Worker yang tidak mendapat chunk tetap benar-benar ada, tetapi dicatat terpisah dari working_pids.

MPI rank r menangani chunk r, r+p, r+2p, dan seterusnya. Integer counts atau float64 sums direduksi menggunakan MPI.SUM, processed counts direduksi terpisah, dan final barrier menutup region. MPI.MAX memilih durasi rank terpanjang; absolute timestamps rank tidak dibandingkan. Pengumpulan timing dan worker identity di luar compute region. Hanya rank 0 mencetak JSON.

Semua metode memvalidasi processed_units=N. JSON mencatat run_id, timestamp UTC, algorithm, method, workload_size/unit, process_count, random_seed yang nullable, chunk_size, estimate, error, compute_seconds, status, error_message, worker_pids, serta alias legacy. CLI mengeluarkan compute-region time; subprocess orchestrator mengganti execution_time/timing_scope menjadi E2E serta menambahkan monitoring. Seed legacy pada Midpoint tidak digunakan secara matematis.

## Standard execution interface

`core/simulation_engine.run_simulation(algorithm, method, workload_size, process_count, seed, chunk_size, ...)` membangun subprocess argument array menggunakan sys.executable. Tidak ada shell=True atau command interpolation. MPI benar-benar dipanggil melalui launcher, bukan disimulasikan dengan pool.

stdout/stderr menggunakan file-backed capture untuk menghindari pipe deadlock. Job dashboard memiliki log files yang dapat dibaca ketika berjalan. Timeout dan cancellation diurus pada loop executor; hasil tidak dianggap selesai hanya karena result file parsial ditemukan.

## Process ownership, monitoring, dan cleanup

Windows Job Object memakai KILL_ON_JOB_CLOSE untuk descendants normal. Intel MPI dapat meluncurkan rank di luar parent tree langsung, sehingga semua computational interpreters mendaftar lebih awal dalam direktori registry privat. Token acak dan process creation time menghubungkan identitas ke job, sehingga PID reuse tidak menyebabkan proses lain dibersihkan.

Registry berisi immutable JSON snapshots agar monitor dan writer tidak berlomba melakukan replace atas file yang sedang terbuka di Windows. Parent registry diteruskan ketika benchmark dashboard meluncurkan inner simulation executors. Completion records membawa OS user+system CPU counters; worker pool menggunakan multiprocessing Finalize dan MPI rank melapor sebelum output/finalization.

psutil mengambil RSS dan process CPU counters setiap 100 ms untuk tiap simulasi; monitor outer benchmark memakai 200 ms. Mean CPU adalah accounted CPU seconds dibagi E2E dan jumlah logical CPU, dikali 100. Nilai ini mencakup startup yang diamati dan final counters dari worker/rank. CPU peak/live merupakan interval samples, sehingga burst pendek dapat terlewat. RSS adalah puncak snapshot jumlah RSS proses job, bukan unique physical memory; shared pages dihitung berulang. Tidak semua helper yang sangat singkat pasti teramati.

Cancel/timeout menandai registry, menutup Job Object, dan menghentikan proses yang terasosiasi dengan token/birth identity melalui psutil, lalu menunggu terminasi. Late-starting owned processes memeriksa marker sebelum komputasi. Cancellation MPI diuji terhadap rank yang berada di luar launcher tree.

## Benchmark methodology

Setiap algoritma memiliki sequential baseline sendiri. Group keys adalah algorithm, method, N, p, seed, dan chunk_size. Speedup = median(T_seq_alg)/median(T_parallel_alg,p); efficiency = speedup/p. Rasio dihitung dari median, bukan median dari rasio individual.

Timer primary perf_counter mencakup proses launch sampai selesai/cleanup. Compute timer tidak dicampur dengan E2E. Monitoring overhead dan PID registry konsisten diaktifkan untuk semua metode baru. Child numerical-library threads dibatasi satu. Konfigurasi dijalankan bergiliran, urutan diacak secara reproducible pada setiap round. Optional warm-ups berupa fresh commands dan tidak masuk CSV terukur.

CSV disimpan incremental. Setelah sukses, summary dan konfigurasi-level ratios dihitung serta metadata diberi complete. Failed/cancelled/interrupted tidak dipromosikan menjadi completed data. Dataset legacy tanpa monitoring dipertahankan tetapi tidak digabung ke baseline baru. Pilot awal dual-algorithm dengan launcher-only monitoring tidak digunakan untuk pembahasan CPU/RSS final.

Strong scaling mempertahankan total N. Model Amdahl klasik S(p)=1/[s+(1-s)/p] tidak memasukkan process-dependent overhead. Interpretasi proyek menambahkan startup/coordination costs secara kualitatif; tidak ada fitting fraksi serial atau klaim komunikasi murni dari selisih median timer.

## Dashboard architecture

`dashboard/app.py` menyediakan sidebar delapan workspace dan dark scientific theme. `views.py` menangani kontrol/halaman; `charts.py` menyusun Plotly; `components.py` menyediakan data access, cached environment inspection, dan shared job panel. CSS/font lokal menghindari external visual dependency.

`ExecutionManager` adalah singleton module yang bertahan saat Streamlit rerun dan navigasi. Background thread menjalankan subprocess; compute tidak berlangsung di rendering cycle. OS file lock mencegah heavy job kedua pada storage workspace yang sama. Form submit merupakan satu-satunya pemicu manual kalkulasi; refresh tidak mengulang job.

Lifecycle adalah STARTING→RUNNING→COMPLETED/FAILED/CANCELLED. Setelah owner process berhenti sebelum terminal state, recovery menandai INTERRUPTED, bukan completed. Browser baru dapat membaca identitas job yang masih berjalan; cancel request file dapat diteruskan kepada owner. Tidak ada database.

Streamlit fragment memperbarui job panel setiap 1 detik dan system monitoring setiap 2 detik selama session aktif. Jika progress kuantitatif tidak diinstrumentasi, UI hanya menampilkan status serta elapsed time nyata. Monitoring CPU/RAM system-wide dipisahkan dari dashboard process dan proses job.

## Visualisasi dan history

Monte Carlo menggunakan Scattergl untuk maksimal 4,000 titik dari prefix stream chunk yang sama. Inside percentage/estimate subset diberi label subset; hasil penuh ditampilkan terpisah. Midpoint menggunakan 4–120 rectangles educational dengan kurva f(x), sehingga tidak menggambar jutaan interval.

Benchmark memiliki execution time, speedup+ideal line, efficiency, algorithm/method comparison, error, CPU/RSS, serta compute strong scaling. Equal N lintas algoritma tidak dianggap equal arithmetic work. Threshold comparison memilih observasi yang benar-benar memenuhi error, tanpa estimasi stopping time.

`DataStore` menyimpan per-run JSON atomik dan menyediakan export CSV. Atomic replace di Windows menggunakan retry singkat untuk handle pembaca yang masih terbuka. History mendukung filter, sorting, result/log details, comparison, dan unduhan. Job benchmark menghasilkan CSV/summary/metadata, resource history, PNG, dan Markdown report.

`plot_results.py` tetap mendukung CSV Monte Carlo lama dan mengekspor 300 DPI. Generator report memakai actual data dan metadata complete. Render/export time berada di luar timing tiap konfigurasi.

## Pengujian dan reproduksi

Backend phase gate dijalankan sebelum dashboard: kedua algoritma dan seluruh execution models harus lulus atau MPI blocker eksternal harus terdokumentasi. Proyek ini memiliki MPI yang benar-benar berfungsi.

Pytest mencakup six configurations, seeded streams, independent scalar midpoint reference, convergence, disjoint interval coverage, worker/rank identity, invalid inputs, timeout, process cleanup, cancellation MPI, resource-rank coverage, lock exclusion, durable history, stale-owner recovery, benchmark baseline integrity, plotting/reporting, delapan halaman AppTest, actual UI submission, cancellation/reset, dan Compare All Six.

AppTest memeriksa rendering dan interaksi Python Streamlit; ini tidak menggantikan inspeksi pixel di browser. Server launcher juga diperiksa menggunakan HTTP health dan HTML response. Browser automation tool tidak tersedia dalam sesi ini. Jalankan README setup, tests, pilot, matrix, plot, report, dan launcher untuk reproduksi.

## Referensi primer

- [Python multiprocessing](https://docs.python.org/3.11/library/multiprocessing.html)
- [NumPy parallel random generation](https://numpy.org/doc/stable/reference/random/parallel.html)
- [mpi4py installation](https://mpi4py.readthedocs.io/en/stable/install.html)
- [Streamlit fragment](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)
- [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
- [psutil](https://psutil.readthedocs.io/)

