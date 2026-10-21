"""Actual psutil measurements; sampled process-tree metrics are not a profiler."""
import os
import json
from pathlib import Path
from time import perf_counter

import psutil


def system_snapshot():
    memory = psutil.virtual_memory()
    process = psutil.Process()
    return dict(cpu_percent=psutil.cpu_percent(interval=None),
                per_cpu_percent=psutil.cpu_percent(interval=None, percpu=True),
                memory_percent=memory.percent, memory_used_mb=memory.used / 2**20,
                memory_total_gb=memory.total / 2**30, application_rss_mb=process.memory_info().rss / 2**20,
                physical_cores=psutil.cpu_count(logical=False), logical_cpus=psutil.cpu_count(),
                application_pid=os.getpid())


class TreeSampler:
    def __init__(self, pid, registry=None, token=None):
        try:
            self.root = psutil.Process(pid)
        except psutil.Error:
            self.root = None
        self.started = self.previous_time = perf_counter()
        self.previous_cpu = {}
        self.accounted_cpu = {}
        self.registry = Path(registry) if registry else None
        self.token = token
        self.observed = {}
        self.samples = []
        psutil.cpu_percent(interval=None)

    def sample(self):
        now = perf_counter()
        try:
            processes = [self.root, *self.root.children(recursive=True)] if self.root else []
        except psutil.Error:
            processes = []
        processes.extend(self.registered_processes())
        # Also retain identities already observed when a redirector/launcher exits early.
        identities = {(p.pid, p.create_time()): p for p in processes if self._accessible(p)}
        identities.update(self.observed)
        rss, delta_cpu, alive = 0, 0.0, []
        for identity, process in identities.items():
            try:
                if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                    self.observed.pop(identity, None)
                    self.previous_cpu.pop(identity, None)
                    continue
                with process.oneshot():
                    cpu = process.cpu_times()
                    seconds = cpu.user + cpu.system
                    self.accounted_cpu[identity] = max(seconds, self.accounted_cpu.get(identity, 0.0))
                    rss += process.memory_info().rss
                    alive.append(dict(pid=process.pid, parent_pid=process.ppid(), name=process.name()))
                if identity in self.previous_cpu:
                    delta_cpu += max(0.0, seconds - self.previous_cpu[identity])
                self.previous_cpu[identity] = seconds
                self.observed[identity] = process
            except psutil.Error:
                self.observed.pop(identity, None)
                self.previous_cpu.pop(identity, None)
                continue
        period = max(now - self.previous_time, 1e-9)
        row = dict(elapsed_seconds=now - self.started,
                   app_cpu_percent=100.0 * delta_cpu / period / (psutil.cpu_count() or 1),
                   app_rss_mb=rss / 2**20, tree_process_count=len(alive),
                   system_cpu_percent=psutil.cpu_percent(interval=None),
                   system_memory_percent=psutil.virtual_memory().percent)
        self.previous_time = now
        self.samples.append(row)
        return row, alive

    def registered_processes(self):
        found = []
        if not self.registry:
            return found
        for path in self.registry.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if record["token"] != self.token:
                    continue
                identity = record["pid"], record["created"]
                if "cpu_seconds" in record:
                    self.accounted_cpu[identity] = max(record["cpu_seconds"], self.accounted_cpu.get(identity, 0.0))
                process = psutil.Process(record["pid"])
                if record["token"] == self.token and abs(process.create_time() - record["created"]) < 0.01:
                    found.append(process)
            except (OSError, ValueError, KeyError, psutil.Error):
                continue
        return found

    @staticmethod
    def _accessible(process):
        try:
            process.create_time()
            return True
        except psutil.Error:
            return False

    def metrics(self, elapsed=None):
        # Mean uses OS CPU-time counters (including worker completion records).
        # Peak is an interval sample and can miss short bursts.
        rows = self.samples[1:]
        wall = elapsed or (self.samples[-1]["elapsed_seconds"] if self.samples else 0)
        return dict(cpu_mean_percent=100.0 * sum(self.accounted_cpu.values()) / wall / (psutil.cpu_count() or 1) if wall > 0 else None,
                    cpu_peak_percent=max((r["app_cpu_percent"] for r in rows), default=None),
                    peak_rss_mb=max((r["app_rss_mb"] for r in self.samples), default=None),
                    monitoring_samples=len(self.samples))
