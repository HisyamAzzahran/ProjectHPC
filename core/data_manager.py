"""Atomic per-job JSON storage and CSV exports without a database."""
import json
import os
import time
from pathlib import Path
from uuid import uuid4

import pandas as pd

from environment import ROOT


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            # Windows readers briefly hold a handle without FILE_SHARE_DELETE.
            if attempt == 19:
                raise
            time.sleep(0.01)


class DataStore:
    def __init__(self, root=None):
        self.root = Path(root) if root else ROOT / "results" / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id):
        if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            raise ValueError("invalid job ID")
        return self.root / job_id

    def save(self, record):
        atomic_json(self.job_dir(record["run_id"]) / "job.json", record)

    def read(self, job_id):
        return json.loads((self.job_dir(job_id) / "job.json").read_text(encoding="utf-8"))

    def history(self):
        records = []
        for path in self.root.glob("*/job.json"):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)

    def export_frame(self):
        rows = []
        for record in self.history():
            row = {k: v for k, v in record.items() if not isinstance(v, (dict, list))}
            row.update(record.get("config", {}))
            result = record.get("result") or {}
            for key in ("algorithm", "method", "workload_size", "process_count", "pi_estimate", "absolute_error", "end_to_end_seconds"):
                if key in result:
                    row[key] = result[key]
            rows.append(row)
        return pd.DataFrame(rows)
