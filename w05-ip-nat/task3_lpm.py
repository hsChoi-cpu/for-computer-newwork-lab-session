class YourTable:
    """Fast longest-prefix-match table using dictionaries grouped by prefix.

    Each prefix length has its own hash table:
        tables[prefix_len][network] = next_hop

    Lookup checks only prefix lengths that actually exist, from longest
    to shortest, and returns immediately on the first match.
    """

    def __init__(self):
        # One dictionary for each possible IPv4 prefix length: /0 ... /32
        self.tables = [{} for _ in range(33)]

        # Prefix lengths that actually exist in the table.
        self.prefixes = []
        self._present = set()

        # Precompute masks so lookup does not rebuild them every time.
        self.masks = [
            0 if plen == 0
            else (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF
            for plen in range(33)
        ]

    def add(self, network, prefix_len, next_hop):
        self.tables[prefix_len][network] = next_hop

        # Only update the prefix list when a new prefix length appears.
        if prefix_len not in self._present:
            self._present.add(prefix_len)
            self.prefixes = sorted(self._present, reverse=True)

    def lookup(self, address):
        # Local references reduce repeated attribute lookups in this hot path.
        tables = self.tables
        masks = self.masks

        # Longest prefix first.
        for plen in self.prefixes:
            network = address & masks[plen]
            hop = tables[plen].get(network)

            if hop is not None:
                return hop

        return None
