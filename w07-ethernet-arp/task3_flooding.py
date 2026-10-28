
#!/usr/bin/env python3
"""Week 7 · Task 3 — A switch that runs out of room.

Textbook §6.4.3.

Compare FIFO-based MAC table eviction against a
frequency-based policy with admission control.

    python3 bench.py
    python3 bench.py --yours
"""

from collections import OrderedDict


class NaiveSwitch:
    """Correct. Evicts the oldest entry."""

    BROADCAST = "ff:ff:ff:ff:ff:ff"

    def __init__(self, ports, capacity):
        self.ports = ports
        self.capacity = capacity
        self.table = OrderedDict()

    def handle(self, frame, in_port):
        src, dst, now = frame

        if src not in self.table and len(self.table) >= self.capacity:
            self.table.popitem(last=False)

        self.table[src] = in_port

        if dst == self.BROADCAST or dst not in self.table:
            return [
                p for p in range(self.ports)
                if p != in_port
            ]

        out = self.table[dst]
        return [] if out == in_port else [out]


class YourSwitch:
    """Frequency-based learning switch with admission control.

    Interface:
        __init__(ports, capacity)
        handle((src, dst, time), in_port)

    The forwarding table stores at most `capacity`
    MAC-to-port mappings.

    Historical frequency information contains no
    port mappings and is used only for eviction.
    """

    BROADCAST = "ff:ff:ff:ff:ff:ff"

    def __init__(self, ports, capacity):
        self.ports = ports
        self.capacity = capacity

        # MAC -> port
        self.table = {}

        # MAC -> observed frequency
        self.freq = {}

        # Number of processed frames
        self.frame_count = 0

        # Period for reducing historical frequency
        self.DECAY_INTERVAL = 4096

    def _update_frequency(self, mac):
        """Record one observation of a MAC address."""

        if mac == self.BROADCAST:
            return

        self.freq[mac] = self.freq.get(mac, 0) + 1

    def _decay_frequency(self):
        """Reduce the influence of old traffic."""

        new_freq = {}

        for mac, count in self.freq.items():
            reduced = count // 2

            if reduced > 0:
                new_freq[mac] = reduced

        self.freq = new_freq

    def _select_victim(self):
        """Find the least frequently used table entry."""

        return min(
            self.table,
            key=lambda mac: self.freq.get(mac, 0)
        )

    def handle(self, frame, in_port):
        src, dst, now = frame

        # --------------------------------------------------
        # Step 1: Update traffic statistics
        # --------------------------------------------------
        self.frame_count += 1

        if self.frame_count % self.DECAY_INTERVAL == 0:
            self._decay_frequency()

        self._update_frequency(src)
        self._update_frequency(dst)

        # --------------------------------------------------
        # Step 2: Learn or update the source MAC
        # --------------------------------------------------

        if src in self.table:
            # Station may have moved to another port.
            self.table[src] = in_port

        elif len(self.table) < self.capacity:
            # Free space: admit the new station.
            self.table[src] = in_port

        elif self.capacity > 0:
            # Table is full: consider replacing an entry.
            victim = self._select_victim()

            new_score = self.freq.get(src, 0)
            old_score = self.freq.get(victim, 0)

            # Admission control:
            # Reject a newcomer if it is less useful.
            if new_score > old_score:
                del self.table[victim]
                self.table[src] = in_port

        # --------------------------------------------------
        # Step 3: Determine forwarding ports
        # --------------------------------------------------

        # Broadcast always floods.
        if dst == self.BROADCAST:
            return [
                p for p in range(self.ports)
                if p != in_port
            ]

        # Known destination: unicast forwarding.
        if dst in self.table:
            out_port = self.table[dst]

            if out_port == in_port:
                return []

            return [out_port]

        # Unknown destination: flooding.
        return [
            p for p in range(self.ports)
            if p != in_port
        ]
