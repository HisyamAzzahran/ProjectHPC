"""Sequential NumPy baseline for Monte Carlo and Midpoint integration."""
from core.process_registry import register_process
register_process("sequential_startup")
from core.numerical_execution import sequential
from monte_carlo import common_parser, positive_int, print_result


def simulate(samples=1_000_000, seed=2026, chunk_size=100_000, algorithm="monte_carlo"):
    return sequential(algorithm, samples, seed, chunk_size)


def main():
    parser = common_parser(__doc__)
    parser.add_argument("--processes", type=positive_int, default=1)
    args = parser.parse_args()
    if args.processes != 1:
        parser.error("sequential execution requires --processes 1")
    try:
        result = simulate(args.samples, args.seed, args.chunk_size, args.algorithm)
    except ValueError as exc:
        parser.error(str(exc))
    print_result(result, args.json)


if __name__ == "__main__":
    main()

