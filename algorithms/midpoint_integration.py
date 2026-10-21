"""Memory-bounded float64 midpoint integration of 4 / (1 + x*x)."""
import numpy as np


def iter_tasks(intervals, chunk_size, rank=0, processes=1):
    if not 0 < intervals <= 2**52 or chunk_size <= 0:
        raise ValueError("intervals must be in [1, 2^52]; chunk size must be positive")
    if processes <= 0 or not 0 <= rank < processes:
        raise ValueError("invalid rank or process count")
    for index in range(rank, (intervals + chunk_size - 1) // chunk_size, processes):
        start = index * chunk_size
        yield index, start, min(chunk_size, intervals - start), intervals


def integrate_chunk(task):
    _, start, count, intervals = task
    x = np.arange(start, start + count, dtype=np.float64)
    x += 0.5
    x /= intervals
    np.square(x, out=x)
    x += 1.0
    np.divide(4.0, x, out=x)
    return float(np.sum(x, dtype=np.float64)), count
