#!/usr/bin/env python3
"""Week 6 · Task 1 — Link state: build the forwarding table yourself."""

import argparse
import heapq

# Undirected weighted graph: node -> {neighbour: cost}
TOPOLOGY = {
    "u": {"v": 2, "w": 5, "x": 1},
    "v": {"u": 2, "w": 3, "x": 2},
    "w": {"u": 5, "v": 3, "x": 3, "y": 1, "z": 5},
    "x": {"u": 1, "v": 2, "w": 3, "y": 1},
    "y": {"w": 1, "x": 1, "z": 2},
    "z": {"w": 5, "y": 2},
}


def dijkstra(graph, source):
    """Shortest path cost from `source` to every node.

    Return {node: cost}. Unreachable nodes must not appear.
    """
    dist = {source: 0}
    pq = [(0, source)]

    while pq:
        cost, node = heapq.heappop(pq)

        # 이미 더 짧은 경로가 발견된 오래된 항목이면 무시
        if cost != dist[node]:
            continue

        for neighbor, weight in graph[node].items():
            new_cost = cost + weight

            if neighbor not in dist or new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                heapq.heappush(pq, (new_cost, neighbor))

    # source 자신은 결과에서 제외
    dist.pop(source, None)

    return dist


def forwarding_table(graph, source):
    """Return {destination: first_hop}."""

    # node -> (cost, first_hop)
    best = {source: (0, "")}

    # (cost, first_hop, current_node)
    pq = [(0, "", source)]

    while pq:
        cost, first_hop, node = heapq.heappop(pq)

        if best.get(node) != (cost, first_hop):
            continue

        for neighbor, weight in graph[node].items():
            # source에서 바로 나가는 경우 현재 이웃이 첫 홉
            if node == source:
                new_first_hop = neighbor
            else:
                new_first_hop = first_hop

            new_cost = cost + weight

            # source 자신으로 돌아오는 경로는 필요 없음
            if neighbor == source:
                continue

            candidate = (new_cost, new_first_hop)

            if neighbor not in best or candidate < best[neighbor]:
                best[neighbor] = candidate
                heapq.heappush(
                    pq,
                    (new_cost, new_first_hop, neighbor)
                )

    return {
        destination: first_hop
        for destination, (cost, first_hop) in best.items()
        if destination != source
    }


def link_down(graph, a, b):
    """A copy of `graph` with the link a-b removed, in both directions."""
    g = {n: dict(e) for n, e in graph.items()}
    g[a].pop(b, None)
    g[b].pop(a, None)
    return g


# ------------------------------------------------------------------- harness
EXPECTED_COST_U = {"v": 2, "w": 3, "x": 1, "y": 2, "z": 4}
EXPECTED_TABLE_U = {"v": "v", "w": "x", "x": "x", "y": "x", "z": "x"}


def verify():
    fails = 0
    try:
        cost = dijkstra(TOPOLOGY, "u")
    except NotImplementedError:
        print("  dijkstra is still a stub")
        return 1

    ok = cost == EXPECTED_COST_U
    print(f"  {'ok  ' if ok else 'FAIL'}  costs from u: {cost}")
    if not ok:
        print(f"        expected {EXPECTED_COST_U}")
    fails += not ok

    try:
        table = forwarding_table(TOPOLOGY, "u")
    except NotImplementedError:
        print("  forwarding_table is still a stub")
        return 1

    ok = table == EXPECTED_TABLE_U
    print(f"  {'ok  ' if ok else 'FAIL'}  table at u:  {table}")
    if not ok:
        print(f"        expected {EXPECTED_TABLE_U}")
    fails += not ok

    for n in TOPOLOGY:
        t = forwarding_table(TOPOLOGY, n)
        missing = set(TOPOLOGY) - {n} - set(t)
        bad = [d for d, h in t.items() if h not in TOPOLOGY[n]]
        ok = not missing and not bad

        print(
            f"  {'ok  ' if ok else 'FAIL'}  "
            f"table at {n} covers all, hops are neighbours"
            + (f"  missing={missing} bad={bad}" if not ok else "")
        )
        fails += not ok

    cut = link_down(TOPOLOGY, "u", "x")
    after = forwarding_table(cut, "u")
    ok = after != table

    print(
        f"  {'ok  ' if ok else 'FAIL'}  "
        f"u reroutes when u-x goes down: {after}"
    )
    fails += not ok

    print(f"\n  {'all ok' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
