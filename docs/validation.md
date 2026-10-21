# Execution and Validation Record

Executed locally on **20 October 2026 (Asia/Jakarta)**. The benchmark metadata retains UTC timestamps. This record distinguishes executed checks from optional future experiments.

## Environment inspected

| Item | Observed value |
|---|---|
| Interpreter | CPython 3.11.9, 64-bit AMD64 |
| Existing environment | `.venv\Scripts\python.exe` |
| CPU | Intel Core i7-10750H CPU @ 2.60GHz |
| Physical / logical CPUs | 6 / 12; 12 available through affinity |
| OS-reported physical RAM | 34,114,936,832 bytes, approximately 31.77 GiB |
| Platform API | `Windows-10-10.0.26300-SP0` |
| Registry observations | ProductName `Windows 10 Home Single Language`; DisplayVersion `26H2`; build `26300` |
| MPI | Intel MPI Library 2021.18.1 for Windows |
| MPI launcher | `.venv\Library\bin\mpiexec.exe` |
| Package state | All five direct requirements already installed in the original environment |

The OS strings above are literal observations, rather than an inferred Windows edition. Initial CIM queries were denied, so read-only native Windows APIs and registry inspection provided CPU topology and RAM. `python` on PATH works; `py -0p` reports no registered interpreters. All reproduction commands use explicit virtual environment paths.

## Source and configuration delivered

- Shared NumPy kernel and CLI helpers in `monte_carlo.py`.
- Executable sequential, multiprocessing, MPI, and MPI hello programs.
- Benchmark runner, scientific plotting program, environment inventory, and measured-report generator.
- Nine automated unittest cases with multiple process-count and argument subtests.
- Pinned direct dependencies, project ignore rules, and VS Code interpreter/test-discovery defaults.
- README, project proposal, technical documentation, measured discussion, and this validation record.

The starter ZIP was inspected and retained unchanged. Its fixed global chunk concept informed the implementation; source files were created in the workspace with the required NumPy kernel and consistent benchmark timing.

## Successful smoke commands

Executed from the workspace in PowerShell:

```powershell
.\.venv\Scripts\python.exe sequential.py --samples 100000
.\.venv\Scripts\python.exe multiprocessing_pi.py --samples 100000 --processes 2
& .\.venv\Library\bin\mpiexec.exe -n 2 .\.venv\Scripts\python.exe hello_mpi.py
& .\.venv\Library\bin\mpiexec.exe -n 2 .\.venv\Scripts\python.exe mpi_pi.py --samples 100000
```

The hello command reported ranks 0 and 1 of 2. All three estimators reported 78,676 hits, 100,000 processed samples, estimated pi 3.14704, and absolute error 0.0054473464102069435. Compute times differ and are not used as primary speedup measurements.

## Automated checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q monte_carlo.py sequential.py multiprocessing_pi.py mpi_pi.py hello_mpi.py environment.py benchmark.py plot_results.py report_results.py tests
```

The final original-environment suite completed **9 tests in 20.511 seconds: OK, zero failures, zero skips**. MPI tests really executed. Dependency checking reported no broken requirements. Source compilation succeeded. The absolute-path launcher override and VS Code JSON syntax were also verified.

Coverage includes plausible pi estimates, deterministic chunk coverage without missing/duplicate indices, non-divisible work, repeated seeds, spawn workers at p=1/2/4, idle workers, MPI collectives at p=1/2/4, idle MPI ranks, useful CLI validation, a real small benchmark, correct median ratios, warm-up exclusion, CSV schema, 300 DPI figure generation, and measured-report generation. Tests use actual child processes, not simulated parallel results.

## Executed experiments and outputs

```powershell
.\.venv\Scripts\python.exe benchmark.py --samples 1000000 --processes 1 2 4 --repeats 3 --output results/pilot.csv
.\.venv\Scripts\python.exe benchmark.py --samples 100000 1000000 5000000 --processes 1 2 4 6 --repeats 3 --warmups 1
.\.venv\Scripts\python.exe plot_results.py
.\.venv\Scripts\python.exe report_results.py
```

| Output | Verified result |
|---|---|
| `results/pilot.csv` | 21 measured rows across 7 configurations |
| `results/benchmark.csv` | 81 measured rows across 27 configurations; three repetitions each |
| `results/benchmark_summary.csv` | 27 median-based summaries |
| `results/benchmark.metadata.json` | Complete status; hardware/software/arguments recorded; 27 discarded warm-ups |
| `figures/` | 11 PNG files; DPI metadata approximately 299.9994 in both dimensions, the PNG encoding of 300 DPI |
| `docs/results_and_discussion.md` | Generated tables and conclusions from the actual CSV and metadata |

Independent output checks confirmed matching hits across methods for every N, exact processed-sample counts, compute time below end-to-end time on all 81 rows, three measured repetitions per configuration, and the expected figure count. One execution-time plot was visually inspected for legibility. All local Markdown links resolve.

The primary experiment found sequential NumPy fastest end to end in every tested workload. MPI had lower median end-to-end time than multiprocessing in all 12 matched (N,p) comparisons. These are local descriptive results, not a universal ranking or a claim about larger unmeasured workloads. Full tables and limitations are in the measured discussion.

## Clean virtual environment verification

A separate `.venv-repro` was created without reusing installed site-packages:

```powershell
.\.venv\Scripts\python.exe -m venv .venv-repro
.\.venv-repro\Scripts\python.exe -m pip install --disable-pip-version-check --cache-dir .cache/pip -r requirements.txt
.\.venv-repro\Scripts\python.exe -m pip check
.\.venv-repro\Scripts\python.exe sequential.py --samples 100000 --json
.\.venv-repro\Scripts\python.exe multiprocessing_pi.py --samples 100000 --processes 2 --json
& .\.venv-repro\Library\bin\mpiexec.exe -n 2 .\.venv-repro\Scripts\python.exe hello_mpi.py
& .\.venv-repro\Library\bin\mpiexec.exe -n 2 .\.venv-repro\Scripts\python.exe mpi_pi.py --samples 100000 --json
.\.venv-repro\Scripts\python.exe -m unittest discover -s tests -v
```

The initial download attempt encountered the execution sandbox's network restriction. Retrying with approved network access succeeded; an existing package-download cache was also reused. This was an installation access issue, not a missing package-version error.

Installed direct requirements: **NumPy 2.4.6, Pandas 3.0.6, Matplotlib 3.11.2, mpi4py 4.1.2, and impi-rt 2021.18.1**. Installed transitive dependencies: contourpy 1.3.3, cycler 0.12.1, fonttools 4.67.0, kiwisolver 1.5.1, packaging 26.3, pillow 13.0.0, pyparsing 3.3.3, python-dateutil 2.9.0.post0, six 1.17.0, and tzdata 2026.5.

The clean environment had no dependency conflicts. Every estimator reproduced the original 78,676 hits at N=100,000. Its full suite completed **9 tests in 18.066 seconds: OK, zero failures, zero skips**, including MPI, real benchmark CSV creation, plotting, and reporting. The clean environment and download cache remain in ignored workspace directories for inspection; the research measurements were not overwritten by these tests.

## Remaining configuration issues

None prevent execution. MPI is functional using the explicit venv launcher. No global PATH, execution policy, firewall, registry, or system-wide package changes were made. Matplotlib uses a writable workspace cache, resolving the initial restricted user-cache warning. Optional 10,000,000-sample experiments, independent-seed statistical studies, and multi-node/weak-scaling experiments were not run or claimed.

