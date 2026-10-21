# Hasil dan Pembahasan

Laporan ini dibangkitkan dari pengukuran aktual. Waktu dapat berubah ketika eksperimen diulang.

## Konfigurasi eksperimen

- Sumber: `dual_algorithm_benchmark.csv`; timestamp UTC: 2026-10-20T15:18:37.740504+00:00.
- CPU: Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz; physical cores: 6; logical CPUs: 12.
- Python: 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)].
- MPI: Intel(R) MPI Library 2021.18.1 for Windows* OS.
- Platform yang dilaporkan OS: Windows-10-10.0.26300-SP0.
- measured observations: 210; warm-up yang dibuang: 0.
- Repetisi per konfigurasi: 3 sampai 3.
- Monitoring: process-tree psutil setiap 100 ms pada eksperimen baru; overhead monitoring termasuk E2E.
- CPU dinormalisasi terhadap kapasitas seluruh logical CPU; RSS dijumlahkan per proses, sehingga shared pages dapat dihitung berulang.
- Mean CPU memakai OS user+system counters termasuk completion readings, dibagi E2E dan logical CPU count. Registry token/creation-time mencakup rank MPI yang terlepas dari launcher tree.

## Results tables

Speedup menggunakan median sequential algoritma yang sama pada N, seed, dan chunk size yang sama. Compute-region tidak dicampur dengan timer E2E.

| Algoritma | N | Metode | p | Median E2E (s) | Min-max E2E (s) | Compute (s) | Speedup | Efficiency |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| midpoint | 100,000 | mpi | 1 | 0.369524 | 0.365280-0.497861 | 0.000538 | 0.7972 | 0.7972 |
| midpoint | 100,000 | mpi | 2 | 0.407369 | 0.402581-0.414093 | 0.000655 | 0.7232 | 0.3616 |
| midpoint | 100,000 | mpi | 4 | 0.492890 | 0.485432-0.514637 | 0.000813 | 0.5977 | 0.1494 |
| midpoint | 100,000 | multiprocessing | 1 | 0.618247 | 0.611519-0.623661 | 0.000937 | 0.4765 | 0.4765 |
| midpoint | 100,000 | multiprocessing | 2 | 0.675541 | 0.630559-0.741526 | 0.001142 | 0.4361 | 0.2180 |
| midpoint | 100,000 | multiprocessing | 4 | 0.736205 | 0.703058-0.800643 | 0.001115 | 0.4001 | 0.1000 |
| midpoint | 100,000 | sequential | 1 | 0.294591 | 0.289925-0.296763 | 0.000598 | 1.0000 | 1.0000 |
| midpoint | 500,000 | mpi | 1 | 0.374887 | 0.368273-0.387070 | 0.001540 | 0.7715 | 0.7715 |
| midpoint | 500,000 | mpi | 2 | 0.401790 | 0.397757-0.442573 | 0.001180 | 0.7198 | 0.3599 |
| midpoint | 500,000 | mpi | 4 | 0.511087 | 0.502724-0.541129 | 0.001991 | 0.5659 | 0.1415 |
| midpoint | 500,000 | multiprocessing | 1 | 0.621025 | 0.615515-0.640827 | 0.002850 | 0.4657 | 0.4657 |
| midpoint | 500,000 | multiprocessing | 2 | 0.650745 | 0.637190-0.672759 | 0.001823 | 0.4444 | 0.2222 |
| midpoint | 500,000 | multiprocessing | 4 | 0.739834 | 0.734883-0.782880 | 0.001803 | 0.3909 | 0.0977 |
| midpoint | 500,000 | sequential | 1 | 0.289210 | 0.284161-0.300677 | 0.001697 | 1.0000 | 1.0000 |
| midpoint | 1,000,000 | mpi | 1 | 0.371813 | 0.367875-0.372386 | 0.005007 | 0.7884 | 0.7884 |
| midpoint | 1,000,000 | mpi | 2 | 0.412874 | 0.401283-0.592407 | 0.002685 | 0.7099 | 0.3550 |
| midpoint | 1,000,000 | mpi | 4 | 0.549531 | 0.511940-0.582156 | 0.002598 | 0.5334 | 0.1333 |
| midpoint | 1,000,000 | multiprocessing | 1 | 0.623103 | 0.607487-0.623527 | 0.004125 | 0.4704 | 0.4704 |
| midpoint | 1,000,000 | multiprocessing | 2 | 0.676666 | 0.649636-0.900422 | 0.003025 | 0.4332 | 0.2166 |
| midpoint | 1,000,000 | multiprocessing | 4 | 0.737527 | 0.736070-0.739815 | 0.003317 | 0.3974 | 0.0994 |
| midpoint | 1,000,000 | sequential | 1 | 0.293119 | 0.287324-0.391140 | 0.005169 | 1.0000 | 1.0000 |
| midpoint | 5,000,000 | mpi | 1 | 0.389686 | 0.383720-0.389769 | 0.021156 | 0.7836 | 0.7836 |
| midpoint | 5,000,000 | mpi | 2 | 0.425106 | 0.414400-0.430563 | 0.012206 | 0.7183 | 0.3592 |
| midpoint | 5,000,000 | mpi | 4 | 0.541636 | 0.511822-0.587872 | 0.009314 | 0.5638 | 0.1409 |
| midpoint | 5,000,000 | multiprocessing | 1 | 0.639088 | 0.634552-0.640133 | 0.015109 | 0.4778 | 0.4778 |
| midpoint | 5,000,000 | multiprocessing | 2 | 0.655111 | 0.649928-0.656995 | 0.010343 | 0.4661 | 0.2331 |
| midpoint | 5,000,000 | multiprocessing | 4 | 0.772801 | 0.743332-0.811011 | 0.007806 | 0.3951 | 0.0988 |
| midpoint | 5,000,000 | sequential | 1 | 0.305369 | 0.299611-0.310025 | 0.012813 | 1.0000 | 1.0000 |
| midpoint | 10,000,000 | mpi | 1 | 0.401798 | 0.400866-0.425332 | 0.041684 | 0.7799 | 0.7799 |
| midpoint | 10,000,000 | mpi | 2 | 0.426748 | 0.419519-0.438147 | 0.022812 | 0.7343 | 0.3671 |
| midpoint | 10,000,000 | mpi | 4 | 0.518948 | 0.502695-0.665726 | 0.017118 | 0.6038 | 0.1510 |
| midpoint | 10,000,000 | multiprocessing | 1 | 0.642822 | 0.639388-0.660649 | 0.029513 | 0.4875 | 0.4875 |
| midpoint | 10,000,000 | multiprocessing | 2 | 0.663784 | 0.658338-0.672204 | 0.020598 | 0.4721 | 0.2360 |
| midpoint | 10,000,000 | multiprocessing | 4 | 0.771050 | 0.757552-0.773834 | 0.013160 | 0.4064 | 0.1016 |
| midpoint | 10,000,000 | sequential | 1 | 0.313346 | 0.307846-0.357679 | 0.025145 | 1.0000 | 1.0000 |
| monte_carlo | 100,000 | mpi | 1 | 0.391714 | 0.388833-0.395685 | 0.018906 | 0.8689 | 0.8689 |
| monte_carlo | 100,000 | mpi | 2 | 0.424694 | 0.422272-0.441028 | 0.019035 | 0.8014 | 0.4007 |
| monte_carlo | 100,000 | mpi | 4 | 0.512797 | 0.512623-0.514121 | 0.020909 | 0.6637 | 0.1659 |
| monte_carlo | 100,000 | multiprocessing | 1 | 0.635842 | 0.624847-0.665839 | 0.017623 | 0.5353 | 0.5353 |
| monte_carlo | 100,000 | multiprocessing | 2 | 0.670321 | 0.660591-1.180292 | 0.018378 | 0.5078 | 0.2539 |
| monte_carlo | 100,000 | multiprocessing | 4 | 0.754095 | 0.734944-0.768231 | 0.018090 | 0.4514 | 0.1128 |
| monte_carlo | 100,000 | sequential | 1 | 0.340368 | 0.306855-0.345623 | 0.020310 | 1.0000 | 1.0000 |
| monte_carlo | 500,000 | mpi | 1 | 0.407462 | 0.390437-0.409871 | 0.024569 | 0.7649 | 0.7649 |
| monte_carlo | 500,000 | mpi | 2 | 0.430875 | 0.428531-0.440117 | 0.022638 | 0.7233 | 0.3617 |
| monte_carlo | 500,000 | mpi | 4 | 0.520299 | 0.507669-0.522448 | 0.023504 | 0.5990 | 0.1498 |
| monte_carlo | 500,000 | multiprocessing | 1 | 0.635208 | 0.632516-0.642686 | 0.022387 | 0.4907 | 0.4907 |
| monte_carlo | 500,000 | multiprocessing | 2 | 0.686206 | 0.676675-0.699092 | 0.020394 | 0.4542 | 0.2271 |
| monte_carlo | 500,000 | multiprocessing | 4 | 0.751960 | 0.746871-0.813082 | 0.022948 | 0.4145 | 0.1036 |
| monte_carlo | 500,000 | sequential | 1 | 0.311672 | 0.305506-0.387369 | 0.025199 | 1.0000 | 1.0000 |
| monte_carlo | 1,000,000 | mpi | 1 | 0.416240 | 0.399074-0.441663 | 0.029636 | 0.7699 | 0.7699 |
| monte_carlo | 1,000,000 | mpi | 2 | 0.438512 | 0.428032-0.441717 | 0.024453 | 0.7308 | 0.3654 |
| monte_carlo | 1,000,000 | mpi | 4 | 0.504617 | 0.503847-0.580901 | 0.027800 | 0.6351 | 0.1588 |
| monte_carlo | 1,000,000 | multiprocessing | 1 | 0.667560 | 0.646848-0.708665 | 0.028804 | 0.4801 | 0.4801 |
| monte_carlo | 1,000,000 | multiprocessing | 2 | 0.667956 | 0.664596-0.678346 | 0.024153 | 0.4798 | 0.2399 |
| monte_carlo | 1,000,000 | multiprocessing | 4 | 0.772756 | 0.753569-0.911323 | 0.026378 | 0.4147 | 0.1037 |
| monte_carlo | 1,000,000 | sequential | 1 | 0.320470 | 0.313153-0.322556 | 0.033157 | 1.0000 | 1.0000 |
| monte_carlo | 5,000,000 | mpi | 1 | 0.453959 | 0.453723-0.459783 | 0.078692 | 0.8037 | 0.8037 |
| monte_carlo | 5,000,000 | mpi | 2 | 0.457369 | 0.444122-0.463788 | 0.052490 | 0.7977 | 0.3988 |
| monte_carlo | 5,000,000 | mpi | 4 | 0.554972 | 0.552931-0.555850 | 0.060253 | 0.6574 | 0.1644 |
| monte_carlo | 5,000,000 | multiprocessing | 1 | 0.690929 | 0.689201-0.694074 | 0.078639 | 0.5280 | 0.5280 |
| monte_carlo | 5,000,000 | multiprocessing | 2 | 0.703842 | 0.687554-0.720333 | 0.053134 | 0.5184 | 0.2592 |
| monte_carlo | 5,000,000 | multiprocessing | 4 | 0.779439 | 0.777877-0.784410 | 0.046293 | 0.4681 | 0.1170 |
| monte_carlo | 5,000,000 | sequential | 1 | 0.364842 | 0.361817-0.367904 | 0.078881 | 1.0000 | 1.0000 |
| monte_carlo | 10,000,000 | mpi | 1 | 0.500624 | 0.492734-0.527795 | 0.139335 | 0.8490 | 0.8490 |
| monte_carlo | 10,000,000 | mpi | 2 | 0.487478 | 0.485360-0.492887 | 0.091062 | 0.8719 | 0.4360 |
| monte_carlo | 10,000,000 | mpi | 4 | 0.569156 | 0.564066-0.650222 | 0.077189 | 0.7468 | 0.1867 |
| monte_carlo | 10,000,000 | multiprocessing | 1 | 0.754594 | 0.741920-0.773170 | 0.143986 | 0.5633 | 0.5633 |
| monte_carlo | 10,000,000 | multiprocessing | 2 | 0.728065 | 0.726307-0.734989 | 0.088636 | 0.5838 | 0.2919 |
| monte_carlo | 10,000,000 | multiprocessing | 4 | 0.810488 | 0.809158-0.827997 | 0.067769 | 0.5244 | 0.1311 |
| monte_carlo | 10,000,000 | sequential | 1 | 0.425041 | 0.420197-0.428141 | 0.141143 | 1.0000 | 1.0000 |

Min-max adalah rentang observasi, bukan confidence interval.

## Akurasi numerik

| Algoritma | N | Estimasi pi | Absolute error |
|---|---:|---:|---:|
| midpoint | 100,000 | 3.1415926535981265 | 8.333334e-12 |
| midpoint | 500,000 | 3.1415926535901262 | 3.335110e-13 |
| midpoint | 1,000,000 | 3.1415926535898762 | 8.304468e-14 |
| midpoint | 5,000,000 | 3.1415926535897967 | 3.552714e-15 |
| midpoint | 10,000,000 | 3.1415926535897940 | 8.881784e-16 |
| monte_carlo | 100,000 | 3.1470400000000001 | 5.447346e-03 |
| monte_carlo | 500,000 | 3.1429840000000002 | 1.391346e-03 |
| monte_carlo | 1,000,000 | 3.1442999999999999 | 2.707346e-03 |
| monte_carlo | 5,000,000 | 3.1428039999999999 | 1.211346e-03 |
| monte_carlo | 10,000,000 | 3.1420651999999998 | 4.725464e-04 |

Monte Carlo diverifikasi dengan inside-count integer yang sama persis; Midpoint diverifikasi dengan toleransi float64. Semua processed count sama dengan N. Seed tidak digunakan oleh Midpoint.

## Execution time, speedup, dan parallel efficiency

### midpoint

Pada N=100,000, median E2E terendah adalah sequential (p=1): 0.294591 s.
Speedup paralel berada pada 0.4001-0.7972; efficiency 0.1000-0.7972.
Pada N=500,000, median E2E terendah adalah sequential (p=1): 0.289210 s.
Speedup paralel berada pada 0.3909-0.7715; efficiency 0.0977-0.7715.
Pada N=1,000,000, median E2E terendah adalah sequential (p=1): 0.293119 s.
Speedup paralel berada pada 0.3974-0.7884; efficiency 0.0994-0.7884.
Pada N=5,000,000, median E2E terendah adalah sequential (p=1): 0.305369 s.
Speedup paralel berada pada 0.3951-0.7836; efficiency 0.0988-0.7836.
Pada N=10,000,000, median E2E terendah adalah sequential (p=1): 0.313346 s.
Speedup paralel berada pada 0.4064-0.7799; efficiency 0.1016-0.7799.

### monte_carlo

Pada N=100,000, median E2E terendah adalah sequential (p=1): 0.340368 s.
Speedup paralel berada pada 0.4514-0.8689; efficiency 0.1128-0.8689.
Pada N=500,000, median E2E terendah adalah sequential (p=1): 0.311672 s.
Speedup paralel berada pada 0.4145-0.7649; efficiency 0.1036-0.7649.
Pada N=1,000,000, median E2E terendah adalah sequential (p=1): 0.320470 s.
Speedup paralel berada pada 0.4147-0.7699; efficiency 0.1037-0.7699.
Pada N=5,000,000, median E2E terendah adalah sequential (p=1): 0.364842 s.
Speedup paralel berada pada 0.4681-0.8037; efficiency 0.1170-0.8037.
Pada N=10,000,000, median E2E terendah adalah sequential (p=1): 0.425041 s.
Speedup paralel berada pada 0.5244-0.8719; efficiency 0.1311-0.8490.

## Konsumsi sumber daya

| Algoritma | Metode | p | N | Median sampled peak RSS (MiB) | Median mean CPU (%) |
|---|---|---:|---:|---:|---:|
| midpoint | mpi | 1 | 100,000 | 41.50 | 4.58 |
| midpoint | mpi | 2 | 100,000 | 69.32 | 9.43 |
| midpoint | mpi | 4 | 100,000 | 119.16 | 17.17 |
| midpoint | multiprocessing | 1 | 100,000 | 76.42 | 4.90 |
| midpoint | multiprocessing | 2 | 100,000 | 96.88 | 7.90 |
| midpoint | multiprocessing | 4 | 100,000 | 150.09 | 12.56 |
| midpoint | sequential | 1 | 100,000 | 34.88 | 4.86 |
| midpoint | mpi | 1 | 500,000 | 40.44 | 4.60 |
| midpoint | mpi | 2 | 500,000 | 67.79 | 7.94 |
| midpoint | mpi | 4 | 500,000 | 120.93 | 16.58 |
| midpoint | multiprocessing | 1 | 500,000 | 74.59 | 6.56 |
| midpoint | multiprocessing | 2 | 500,000 | 107.00 | 8.13 |
| midpoint | multiprocessing | 4 | 500,000 | 168.94 | 13.90 |
| midpoint | sequential | 1 | 500,000 | 34.25 | 5.96 |
| midpoint | mpi | 1 | 1,000,000 | 41.21 | 5.24 |
| midpoint | mpi | 2 | 1,000,000 | 70.00 | 9.09 |
| midpoint | mpi | 4 | 1,000,000 | 119.91 | 15.26 |
| midpoint | multiprocessing | 1 | 1,000,000 | 75.85 | 5.64 |
| midpoint | multiprocessing | 2 | 1,000,000 | 104.10 | 9.04 |
| midpoint | multiprocessing | 4 | 1,000,000 | 171.62 | 12.91 |
| midpoint | sequential | 1 | 1,000,000 | 34.69 | 5.66 |
| midpoint | mpi | 1 | 5,000,000 | 41.91 | 5.35 |
| midpoint | mpi | 2 | 5,000,000 | 69.59 | 9.11 |
| midpoint | mpi | 4 | 5,000,000 | 121.29 | 16.17 |
| midpoint | multiprocessing | 1 | 5,000,000 | 74.22 | 5.30 |
| midpoint | multiprocessing | 2 | 5,000,000 | 107.79 | 8.61 |
| midpoint | multiprocessing | 4 | 5,000,000 | 171.43 | 12.81 |
| midpoint | sequential | 1 | 5,000,000 | 40.16 | 6.72 |
| midpoint | mpi | 1 | 10,000,000 | 40.90 | 6.16 |
| midpoint | mpi | 2 | 10,000,000 | 69.42 | 8.24 |
| midpoint | mpi | 4 | 10,000,000 | 121.39 | 15.81 |
| midpoint | multiprocessing | 1 | 10,000,000 | 74.90 | 5.91 |
| midpoint | multiprocessing | 2 | 10,000,000 | 107.85 | 8.50 |
| midpoint | multiprocessing | 4 | 10,000,000 | 172.38 | 12.96 |
| midpoint | sequential | 1 | 10,000,000 | 41.96 | 6.34 |
| monte_carlo | mpi | 1 | 100,000 | 41.31 | 4.69 |
| monte_carlo | mpi | 2 | 100,000 | 67.93 | 9.15 |
| monte_carlo | mpi | 4 | 100,000 | 120.61 | 16.76 |
| monte_carlo | multiprocessing | 1 | 100,000 | 74.27 | 6.35 |
| monte_carlo | multiprocessing | 2 | 100,000 | 106.75 | 7.49 |
| monte_carlo | multiprocessing | 4 | 100,000 | 170.13 | 13.47 |
| monte_carlo | sequential | 1 | 100,000 | 43.09 | 5.27 |
| monte_carlo | mpi | 1 | 500,000 | 40.10 | 5.11 |
| monte_carlo | mpi | 2 | 500,000 | 68.88 | 10.27 |
| monte_carlo | mpi | 4 | 500,000 | 121.59 | 17.70 |
| monte_carlo | multiprocessing | 1 | 500,000 | 76.04 | 5.67 |
| monte_carlo | multiprocessing | 2 | 500,000 | 105.80 | 8.85 |
| monte_carlo | multiprocessing | 4 | 500,000 | 138.92 | 15.06 |
| monte_carlo | sequential | 1 | 500,000 | 43.99 | 6.05 |
| monte_carlo | mpi | 1 | 1,000,000 | 41.43 | 5.01 |
| monte_carlo | mpi | 2 | 1,000,000 | 68.19 | 9.14 |
| monte_carlo | mpi | 4 | 1,000,000 | 124.32 | 18.83 |
| monte_carlo | multiprocessing | 1 | 1,000,000 | 73.77 | 6.24 |
| monte_carlo | multiprocessing | 2 | 1,000,000 | 110.78 | 8.23 |
| monte_carlo | multiprocessing | 4 | 1,000,000 | 173.57 | 14.72 |
| monte_carlo | sequential | 1 | 1,000,000 | 44.20 | 5.41 |
| monte_carlo | mpi | 1 | 5,000,000 | 56.79 | 5.74 |
| monte_carlo | mpi | 2 | 5,000,000 | 67.85 | 9.55 |
| monte_carlo | mpi | 4 | 5,000,000 | 172.85 | 18.54 |
| monte_carlo | multiprocessing | 1 | 5,000,000 | 76.17 | 6.05 |
| monte_carlo | multiprocessing | 2 | 5,000,000 | 107.79 | 8.86 |
| monte_carlo | multiprocessing | 4 | 5,000,000 | 182.89 | 15.23 |
| monte_carlo | sequential | 1 | 5,000,000 | 45.86 | 5.71 |
| monte_carlo | mpi | 1 | 10,000,000 | 55.84 | 5.92 |
| monte_carlo | mpi | 2 | 10,000,000 | 96.52 | 10.04 |
| monte_carlo | mpi | 4 | 10,000,000 | 172.73 | 19.90 |
| monte_carlo | multiprocessing | 1 | 10,000,000 | 78.79 | 6.49 |
| monte_carlo | multiprocessing | 2 | 10,000,000 | 105.59 | 9.68 |
| monte_carlo | multiprocessing | 4 | 10,000,000 | 177.52 | 13.84 |
| monte_carlo | sequential | 1 | 10,000,000 | 45.87 | 5.82 |

## Strong scaling dan Amdahl's Law

Setiap kurva strong scaling mempertahankan N tetap dan mengubah p. Idealnya S(p)=p dan E(p)=1. Amdahl's Law klasik adalah S(p)=1/[s+(1-s)/p]. Peluncuran interpreter, import NumPy, spawn, dispatch, IPC, dan MPI collective menambah biaya yang tidak dimodelkan oleh fraksi serial tetap.
Perbedaan E2E dan compute-region mencakup beberapa komponen tersebut sekaligus; selisihnya bukan pengukuran komunikasi murni. Data ini tidak cukup untuk mengidentifikasi atau memfit fraksi serial secara andal.
Satu chunk hanya dapat dikerjakan satu worker/rank. Karena itu N=100,000 dengan chunk size=100,000 tidak menyediakan concurrency komputasi, walaupun proses tambahan benar-benar diluncurkan. Chunk yang tidak habis dibagi p menimbulkan load imbalance.

## Perbandingan kedua algoritma

N adalah jumlah random samples untuk Monte Carlo dan jumlah integration intervals untuk Midpoint. N sama tidak berarti jumlah operasi, kebutuhan random generation, atau target akurasi sama. Monte Carlo memiliki error stokastik dengan expected standard deviation O(N^-1/2). Midpoint untuk integrand mulus memiliki truncation error O(N^-2), hingga keterbatasan floating-point mendominasi. Error nol terhadap math.pi berarti kesamaan representasi float64, bukan bukti solusi eksak.
Repetisi benchmark memakai seed yang sama untuk memisahkan variasi waktu dari variasi sampel. Repetisi tersebut bukan independent statistical replications. Tidak ada klaim algoritma yang selalu lebih baik atau interpolasi time-to-accuracy di luar pengukuran.

## Keterbatasan

- Satu workstation, local single-node, tanpa multi-node network, weak scaling, atau cluster fisik.
- Tiga repetisi default memberikan median/rentang deskriptif, bukan signifikansi statistik.
- Suhu, power plan, CPU frequency, aplikasi latar belakang, dan MPI affinity tidak dikontrol.
- Peak RSS dan CPU bersifat sampled; proses sangat singkat dapat terlewat dan shared pages tidak dideduplikasi.
- Pengukuran baru dengan monitoring tidak digabung dengan baseline historis tanpa monitoring.
- Waktu render Plotly/Matplotlib dan pembuatan laporan di luar timer benchmark setiap konfigurasi.

## Kesimpulan

Untuk midpoint, 0 dari 30 konfigurasi paralel memiliki median E2E speedup >1. Kesimpulan dibatasi pada matriks dan perangkat ini.
Untuk monte_carlo, 0 dari 30 konfigurasi paralel memiliki median E2E speedup >1. Kesimpulan dibatasi pada matriks dan perangkat ini.

Reproduksi menggunakan README. CSV mentah dan metadata adalah bukti utama; grafik dan tabel berasal dari berkas tersebut.
