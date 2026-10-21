"""Contain and terminate only this application's own subprocess trees."""
import ctypes
import os

import psutil


class ProcessContainer:
    """Windows Job Object closes descendants, including children of MPI launchers."""
    def __init__(self, pid):
        self.pid, self.handle = pid, None
        try:
            self.root = psutil.Process(pid)
        except psutil.Error:
            self.root = None
        self.containment = "psutil process tree"
        if os.name != "nt":
            return
        from ctypes import wintypes as w

        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", w.DWORD), ("minimum_ws", ctypes.c_size_t),
                        ("maximum_ws", ctypes.c_size_t), ("active_limit", w.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(f"counter{i}", ctypes.c_uint64) for i in range(6)]

        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]

        kernel = self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.restype = w.HANDLE
        kernel.OpenProcess.restype = w.HANDLE
        kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        kernel.CloseHandle.argtypes = [w.HANDLE]
        job = kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        process = kernel.OpenProcess(0x0101, False, pid)  # SET_QUOTA | TERMINATE
        if job and process and kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            if kernel.AssignProcessToJobObject(job, process):
                self.handle, self.containment = job, "Windows Job Object"
        if process:
            kernel.CloseHandle(process)
        if job and not self.handle:
            kernel.CloseHandle(job)

    def close(self, observed=()):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
        # Check creation times on observed psutil identities to avoid PID-reuse errors.
        candidates = list(observed)
        try:
            root = self.root
            if root is None or not root.is_running():
                raise psutil.NoSuchProcess(self.pid)
            candidates.extend(root.children(recursive=True))
            candidates.append(root)
        except psutil.Error:
            pass
        alive = []
        for process in candidates:
            try:
                if process.is_running():
                    process.kill()
                    alive.append(process)
            except psutil.Error:
                continue
        if alive:
            psutil.wait_procs(alive, timeout=3)
