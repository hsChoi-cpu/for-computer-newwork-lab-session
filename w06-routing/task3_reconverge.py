#!/usr/bin/env python3
"""Week 6 · Task 3 — Reconverge without recomputing the world."""

import heapq


SPF_RUNS = 0

# 마지막 full SPF에서 얻은 부가 정보.
# dijkstra_table()의 반환값/API는 바꾸지 않는다.
_LAST_DIST = {}
_LAST_PARENT = {}


def dijkstra_table(graph, source):
    """Reference shortest-path-first. Returns {destination: first_hop}."""
    global SPF_RUNS, _LAST_DIST, _LAST_PARENT
    SPF_RUNS += 1

    best = {source: (0, None)}
    parent = {source: None}

    pq, done = [(0, source, None)], set()

    while pq:
        cost, node, first_hop = heapq.heappop(pq)

        if node in done:
            continue

        done.add(node)
        best[node] = (cost, first_hop)

        for nbr, w in sorted(graph[node].items()):
            if nbr in done:
                continue

            hop = nbr if node == source else first_hop
            new_cost = cost + w

            if new_cost < best.get(nbr, (float("inf"), None))[0]:
                best[nbr] = (new_cost, hop)
                parent[nbr] = node
                heapq.heappush(pq, (new_cost, nbr, hop))

    # YourRouter가 full SPF 직후 복사해 둘 부가 정보
    _LAST_DIST = {
        node: cost
        for node, (cost, _) in best.items()
    }
    _LAST_PARENT = dict(parent)

    return {
        d: h
        for d, (_, h) in best.items()
        if d != source and h
    }


class FullRecompute:
    """On every event, forget everything and run SPF again."""

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self.table = dijkstra_table(self.graph, source)

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost

        self.table = dijkstra_table(self.graph, self.source)


class YourRouter:
    """Incremental router."""

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source

        self._full_recompute()

    def _full_recompute(self):
        """Full SPF. Every full recompute must go through dijkstra_table()."""
        global _LAST_DIST, _LAST_PARENT

        self.table = dijkstra_table(self.graph, self.source)

        # harness가 이후 dijkstra_table()을 호출해도 영향을 받지 않도록 복사
        self.dist = dict(_LAST_DIST)
        self.parent = dict(_LAST_PARENT)

    def _pred_key(self, node):
        """Reference Dijkstra의 predecessor 처리 순서와 맞추기 위한 key."""
        if node == self.source:
            hop = ""
        else:
            hop = self.table.get(node, "")

        return (
            self.dist.get(node, float("inf")),
            node,
            hop,
        )

    def _incremental_decrease(self, a, b):
        """새 링크/비용 감소를 기존 최단거리에서 증분 반영한다.

        True 반환:
            tie-breaking 때문에 안전하게 full SPF를 해야 함.
        False 반환:
            증분 갱신만으로 충분함.
        """
        inf = float("inf")
        pq = []

        need_full = False

        def relax(pred, nbr):
            nonlocal need_full

            if need_full:
                return

            # pred 자체가 source에서 도달 불가능하면 새 경로도 만들 수 없다.
            if pred not in self.dist:
                return

            new_cost = self.dist[pred] + self.graph[pred][nbr]

            if pred == self.source:
                new_hop = nbr
            else:
                new_hop = self.table.get(pred)

                if new_hop is None:
                    return

            old_cost = self.dist.get(nbr, inf)

            # 진짜 더 짧은 경로
            if new_cost < old_cost:
                self.dist[nbr] = new_cost

                if nbr != self.source:
                    self.table[nbr] = new_hop

                self.parent[nbr] = pred

                heapq.heappush(
                    pq,
                    (new_cost, nbr, new_hop, pred)
                )

            # 거리 자체는 같지만 reference Dijkstra의 tie-breaking에 의해
            # first hop이 달라질 가능성이 있는 경우
            elif new_cost == old_cost and nbr != self.source:
                current_hop = self.table.get(nbr)
                current_parent = self.parent.get(nbr)

                wins_tie = (
                    current_parent is None
                    or self._pred_key(pred)
                    < self._pred_key(current_parent)
                )

                if wins_tie:
                    # 같은 first hop이라면 table은 그대로이므로
                    # parent만 reference와 맞춰 두면 된다.
                    if new_hop == current_hop:
                        self.parent[nbr] = pred

                    # 같은 거리인데 first hop이 바뀌는 경우는
                    # 안전하게 full SPF로 처리한다.
                    else:
                        need_full = True

        # 변경된 링크 자체부터 relaxation
        relax(a, b)
        relax(b, a)

        if need_full:
            return True

        # 개선된 노드에서만 바깥으로 propagation
        while pq and not need_full:
            cost, node, hop, pred = heapq.heappop(pq)

            # 더 최신의 개선 결과가 이미 존재하는 stale entry
            if cost != self.dist.get(node):
                continue

            if self.table.get(node) != hop:
                continue

            if self.parent.get(node) != pred:
                continue

            for nbr, _ in sorted(self.graph[node].items()):
                if nbr == self.source:
                    continue

                relax(node, nbr)

                if need_full:
                    break

        return need_full

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""

        old_cost = self.graph[a].get(b)

        # 먼저 실제 topology를 변경
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost

        # 실질적으로 변화가 없는 이벤트
        if old_cost == cost:
            return

        # ------------------------------------------------------------
        # Case 1: link down 또는 cost 증가
        # ------------------------------------------------------------
        if cost is None or (
            old_cost is not None and cost > old_cost
        ):
            # 현재 선택된 shortest-path tree가 이 링크를 사용하지 않는다면
            # 현재 forwarding table에는 아무 영향이 없다.
            used = (
                self.parent.get(a) == b
                or self.parent.get(b) == a
            )

            if not used:
                return

            # 사용 중이던 tree edge가 나빠진 경우에는
            # 대체 경로를 전체적으로 찾아야 하므로 full SPF.
            self._full_recompute()
            return

        # ------------------------------------------------------------
        # Case 2: link up 또는 cost 감소
        # ------------------------------------------------------------
        # 경로는 나빠질 수 없고 일부 목적지만 좋아질 수 있으므로
        # 기존 dist를 seed로 incremental relaxation한다.
        need_full = self._incremental_decrease(a, b)

        if need_full:
            self._full_recompute()
