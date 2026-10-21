"""Kernel, real subprocess, MPI collective, CSV, and plotting verification."""

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from benchmark import RAW_COLUMNS, run_one, summarize
from environment import ROOT, find_mpiexec
from monte_carlo import aggregate, count_hits, iter_tasks
from sequential import simulate


class KernelTests(unittest.TestCase):
    def test_valid_pi_estimate(self):
        result = simulate(100_000)
        self.assertLess(abs(result["pi_estimate"] - math.pi), 0.03)
        self.assertEqual(result["processed_samples"], 100_000)

    def test_chunk_coverage_and_nondivisible_distribution(self):
        tasks = list(iter_tasks(1003, 97, 2026))
        for processes in (1, 2, 4, 16):
            distributed = [task for rank in range(processes)
                           for task in iter_tasks(1003, 97, 2026, rank, processes)]
            self.assertEqual(sorted(distributed), tasks)
            self.assertEqual(len({t[0] for t in distributed}), len(tasks))
            self.assertEqual(sum(t[1] for t in distributed), 1003)

    def test_seed_is_deterministic(self):
        task = (3, 1234, 2026)
        self.assertEqual(count_hits(task), count_hits(task))
        result = simulate(1003, 0, 97)
        self.assertEqual(result["hits"], aggregate(map(count_hits, iter_tasks(1003, 97, 0)))[0])

    def test_bad_kernel_configuration(self):
        for config in ((0, 10, 1), (10, 0, 1), (10, 1, -1)):
            with self.subTest(config=config), self.assertRaises(ValueError):
                list(iter_tasks(*config))


class CommandTests(unittest.TestCase):
    def test_multiprocessing_matches_sequential(self):
        baseline = run_one("sequential", 1003, 1, 97, 0)
        for processes in (1, 2, 4):
            with self.subTest(processes=processes):
                result = run_one("multiprocessing", 1003, processes, 97, 0)
                self.assertEqual(result["hits"], baseline["hits"])
                self.assertEqual(result["pi_estimate"], baseline["pi_estimate"])
                self.assertEqual(result["processed_samples"], 1003)
                self.assertGreater(result["end_to_end_seconds"], result["compute_seconds"])

    def test_idle_workers_do_not_duplicate_samples(self):
        baseline = run_one("sequential", 7, 1, 100, 2026)
        result = run_one("multiprocessing", 7, 4, 100, 2026)
        self.assertEqual(result["hits"], baseline["hits"])
        self.assertEqual(result["processed_samples"], 7)

    @unittest.skipUnless(find_mpiexec(), "MPI launcher unavailable")
    def test_mpi_collectives_and_idle_ranks(self):
        for samples, chunk_size, seed, processes in ((1003, 97, 0, 1), (1003, 97, 0, 2),
                                                      (1003, 97, 0, 4), (7, 100, 2026, 4)):
            with self.subTest(samples=samples, processes=processes):
                baseline = simulate(samples, seed, chunk_size)
                result = run_one("mpi", samples, processes, chunk_size, seed)
                self.assertEqual(result["hits"], baseline["hits"])
                self.assertEqual(result["processed_samples"], samples)
                self.assertEqual(result["pi_estimate"], baseline["pi_estimate"])

    def test_invalid_cli_arguments(self):
        cases = [("sequential.py", "--samples", "0"),
                 ("sequential.py", "--chunk-size", "0"),
                 ("sequential.py", "--seed", "-1"),
                 ("mpi_pi.py", "--samples", "-1"),
                 ("multiprocessing_pi.py", "--processes", "0"),
                 ("multiprocessing_pi.py", "--processes", "100000"),
                 ("benchmark.py", "--repeats", "0"),
                 ("benchmark.py", "--methods", "mpi")]
        for script, *args in cases:
            with self.subTest(script=script, args=args):
                completed = subprocess.run([sys.executable, str(ROOT / script), *args],
                                           capture_output=True, text=True, timeout=30)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("error:", completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)

    def test_real_benchmark_csv_and_plots(self):
        from plot_results import generate_plots
        from report_results import generate_report

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.csv"
            completed = subprocess.run(
                [sys.executable, str(ROOT / "benchmark.py"), "--samples", "1003",
                 "--processes", "1", "2", "--repeats", "3", "--warmups", "1",
                 "--methods", "sequential", "multiprocessing", "--chunk-size", "97",
                 "--output", str(path)], capture_output=True, text=True, timeout=120
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            data = pd.read_csv(path)
            self.assertEqual(list(data.columns), RAW_COLUMNS)
            self.assertEqual(len(data), 9)
            self.assertFalse(data.isna().any().any())
            self.assertEqual(data.hits.nunique(), 1)
            summary = summarize(data)
            self.assertEqual(len(summary), 3)
            baseline = summary[summary.method == "sequential"].iloc[0]
            self.assertEqual(baseline.speedup, 1)
            for _, row in summary.iterrows():
                self.assertAlmostEqual(row.speedup, baseline.median_end_to_end_seconds / row.median_end_to_end_seconds)
                self.assertAlmostEqual(row.parallel_efficiency, row.speedup / row.processes)
                self.assertEqual(row.runs, 3)
            metadata = json.loads(path.with_suffix(".metadata.json").read_text())
            self.assertEqual(metadata["warmup_runs"], 3)
            self.assertEqual(metadata["status"], "complete")
            paths = generate_plots(path, Path(temporary) / "figures")
            self.assertEqual(len(paths), 5)
            self.assertTrue(all(p.is_file() and p.stat().st_size > 1000 for p in paths))
            report = generate_report(path, Path(temporary) / "discussion.md")
            self.assertIn("measured observations: 9", report.read_text(encoding="utf-8"))
            self.assertIn("Results tables", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
