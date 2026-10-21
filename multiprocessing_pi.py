"""Windows-safe multiprocessing for both numerical algorithms."""
from core.process_registry import register_process
register_process("multiprocessing_startup")
import multiprocessing as mp
from core.numerical_execution import multiprocessing_run
from monte_carlo import common_parser, cpu_limit, positive_int, print_result


def simulate(samples=1_000_000, processes=2, seed=2026, chunk_size=100_000,
             algorithm="monte_carlo", allow_oversubscribe=False):
    return multiprocessing_run(algorithm, samples, processes, seed, chunk_size, allow_oversubscribe)


def main():
    parser = common_parser(__doc__)
    parser.add_argument("--processes", type=positive_int, default=min(4, cpu_limit()))
    parser.add_argument("--allow-oversubscribe", action="store_true")
    args = parser.parse_args()
    try:
        result = simulate(args.samples, args.processes, args.seed, args.chunk_size,
                          args.algorithm, args.allow_oversubscribe)
    except ValueError as exc:
        parser.error(str(exc))
    print_result(result, args.json)


if __name__ == "__main__":
    mp.freeze_support()
    main()

