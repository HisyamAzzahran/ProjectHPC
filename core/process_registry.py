"""Associate detached MPI ranks with one executor using a private token and birth time."""
import json
import os
from pathlib import Path
from uuid import uuid4


def register_process(role, finished=False):
    directory = os.environ.get("HPC_PROCESS_REGISTRY")
    token = os.environ.get("HPC_JOB_TOKEN")
    if not directory or not token:
        return
    import psutil
    process = psutil.Process()
    record = dict(pid=process.pid, created=process.create_time(), token=token, role=role)
    if finished:
        cpu = process.cpu_times()
        record["cpu_seconds"] = cpu.user + cpu.system
    parents = json.loads(os.environ.get("HPC_PARENT_REGISTRIES", "[]"))
    for registry, registry_token in [(directory, token), *parents]:
        registry = Path(registry)
        if not registry.is_dir() or (registry / "cancel.request").exists():
            if not finished:
                raise SystemExit(130)
            continue
        record["token"] = registry_token
        # Immutable snapshots avoid Windows rename-over-open-file races with monitors.
        path = registry / f"{process.pid}.{uuid4().hex}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record), encoding="utf-8")
        os.replace(temporary, path)
