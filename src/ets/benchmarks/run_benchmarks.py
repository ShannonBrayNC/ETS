import time

from ets.datasets.generator import generate_ticket_events
from ets.log.node import TransparencyNode


def benchmark_append(count=10000):
    node = TransparencyNode("node-a")

    events = generate_ticket_events(count)

    start = time.perf_counter()

    for event in events:
        node.append(event)

    elapsed = time.perf_counter() - start

    return {
        "count": count,
        "elapsed_seconds": elapsed,
        "events_per_second": count / elapsed,
        "root": node.merkle_root(),
    }


if __name__ == "__main__":
    print(benchmark_append())
