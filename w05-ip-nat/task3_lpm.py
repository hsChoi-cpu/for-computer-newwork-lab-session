#!/usr/bin/env python3
"""Week 5 · Task 3 — Make longest-prefix match fast.

Textbook §4.3.3.
"""


class LinearTable:
    """Correct, and slow in the obvious way."""

    def __init__(self):
        self.entries = []  # (prefix_len, network, next_hop)

    def add(self, network, prefix_len, next_hop):
        self.entries.append((prefix_len, network, next_hop))

    def lookup(self, address):
        best = None

        for plen, net, hop in self.entries:
            mask = (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF

            if address & mask == net and (best is None or plen > best[0]):
                best = (plen, hop)

        return best[1] if best else None


class YourTable:
    """Fast longest-prefix-match table grouped by prefix length."""

    def __init__(self):
        # One dictionary for each IPv4 prefix length: /0 through /32
        self.tables = [{} for _ in range(33)]

        # Prefix lengths actually present in the routing table
        self.prefixes = []
        self._present = set()

        # Precompute masks once
        self.masks = [
            0 if plen == 0
            else (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF
            for plen in range(33)
        ]

    def add(self, network, prefix_len, next_hop):
        self.tables[prefix_len][network] = next_hop

        if prefix_len not in self._present:
            self._present.add(prefix_len)
            self.prefixes = sorted(self._present, reverse=True)

    def lookup(self, address):
        tables = self.tables
        masks = self.masks

        # Longest prefix first
        for plen in self.prefixes:
            network = address & masks[plen]
            hop = tables[plen].get(network)

            if hop is not None:
                return hop

        return None
