"""MPI smoke test: every rank reports once, in rank order."""


def main():
    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    messages = comm.gather(f"Hello from rank {comm.rank} of {comm.size}", root=0)
    if comm.rank == 0:
        print("\n".join(messages), flush=True)


if __name__ == "__main__":
    main()

