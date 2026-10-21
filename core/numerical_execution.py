"""In-process sequential execution and real spawn-based worker pools."""
import multiprocessing as mp
import os
from time import perf_counter

from core.workload_manager import aggregate_partials, make_result, process_task, tasks, validate_config
from core.process_registry import register_process


def sequential(algorithm, workload, seed, chunk_size):
    validate_config(algorithm, "sequential", workload, 1, seed, chunk_size)
    register_process("sequential")
    start = perf_counter()
    total, processed, working = aggregate_partials(
        map(process_task, tasks(algorithm, workload, chunk_size, seed)), algorithm)
    elapsed = perf_counter() - start
    register_process("sequential_complete", finished=True)
    return make_result(algorithm, "sequential", workload, 1, seed, chunk_size,
                       total, processed, elapsed, [os.getpid()], working)


def worker_ready(barrier, ready_queue):
    register_process("multiprocessing_worker")
    from multiprocessing.util import Finalize
    Finalize(None, register_process, args=("multiprocessing_worker_complete", True), exitpriority=0)
    ready_queue.put(os.getpid())
    barrier.wait(timeout=60)
    barrier.wait(timeout=60)


def multiprocessing_run(algorithm, workload, processes, seed, chunk_size, allow_oversubscribe=False):
    validate_config(algorithm, "multiprocessing", workload, processes, seed, chunk_size, allow_oversubscribe)
    register_process("multiprocessing_controller")
    context = mp.get_context("spawn")
    barrier, ready_queue = context.Barrier(processes + 1), context.Queue()
    try:
        with context.Pool(processes, initializer=worker_ready, initargs=(barrier, ready_queue)) as pool:
            barrier.wait(timeout=60)
            worker_pids = sorted(ready_queue.get(timeout=60) for _ in range(processes))
            start = perf_counter()
            barrier.wait(timeout=60)
            total, processed, working = aggregate_partials(pool.imap_unordered(
                process_task, tasks(algorithm, workload, chunk_size, seed), chunksize=1), algorithm)
            elapsed = perf_counter() - start
            pool.close()
            pool.join()
            register_process("multiprocessing_controller_complete", finished=True)
    finally:
        ready_queue.close()
        ready_queue.join_thread()
    return make_result(algorithm, "multiprocessing", workload, processes, seed, chunk_size,
                       total, processed, elapsed, worker_pids, working)
