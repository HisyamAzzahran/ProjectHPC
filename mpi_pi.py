"""Real MPI cyclic chunks with integer or float64 SUM collectives."""
from core.process_registry import register_process
register_process("mpi_rank_startup")
import os
from time import perf_counter
from core.workload_manager import aggregate_partials, make_result, process_task, tasks
from monte_carlo import available_cpu_ids, common_parser, print_result


def main():
    parser = common_parser(__doc__)
    parser.add_argument("--allow-oversubscribe", action="store_true")
    args = parser.parse_args()
    if args.algorithm == "midpoint" and args.samples > 2**52:
        parser.error("midpoint workload must not exceed 2^52")
    try:
        from mpi4py import MPI
    except (ImportError, RuntimeError) as exc:
        parser.exit(1, f"MPI unavailable: {exc}\n")
    comm = MPI.COMM_WORLD
    rank, processes = comm.rank, comm.size
    from core.process_registry import register_process
    register_process(f"mpi_rank_{rank}")
    available = len(set().union(*comm.allgather(available_cpu_ids())))
    if processes > available and not args.allow_oversubscribe:
        parser.error("process count exceeds available logical CPUs")
    worker_pids = comm.gather(os.getpid(), root=0)
    try:
        comm.Barrier()
        start = perf_counter()
        local_total, local_count, local_working = aggregate_partials(map(
            process_task, tasks(args.algorithm, args.samples, args.chunk_size, args.seed, rank, processes)
        ), args.algorithm)
        total = comm.reduce(local_total, op=MPI.SUM, root=0)
        processed = comm.reduce(local_count, op=MPI.SUM, root=0)
        comm.Barrier()
        duration = perf_counter() - start
        elapsed = comm.reduce(duration, op=MPI.MAX, root=0)
        working = comm.gather(local_working, root=0)
        register_process(f"mpi_rank_{rank}_complete", finished=True)
        if rank == 0:
            result = make_result(args.algorithm, "mpi", args.samples, processes, args.seed,
                                 args.chunk_size, total, processed, elapsed, sorted(worker_pids),
                                 sorted({pid for group in working for pid in group}))
            print_result(result, args.json)
    except Exception as exc:
        print(f"MPI rank {rank} failed: {exc}", flush=True)
        comm.Abort(1)


if __name__ == "__main__":
    main()

