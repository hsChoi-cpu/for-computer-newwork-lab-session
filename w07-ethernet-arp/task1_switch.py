
#!/usr/bin/env python3
"""Week 7 · Task 1 — Build a learning switch.

Textbook §6.4.3 (link-layer switches, self-learning)
and §6.4.1 (MAC addresses).

A switch is handed a frame and has to decide which ports
to send it out of. It learns MAC addresses by watching
where frames come from.

    python3 task1_switch.py --verify
"""
import argparse


class Switch:
    """A self-learning Ethernet switch.

    `ports` is how many it has, numbered from 0.

    handle(frame, in_port) -> list of ports to forward out of,
    in ascending order.

    A frame is (src_mac, dst_mac, time).
    Time is in seconds and only moves forward.
    """

    BROADCAST = "ff:ff:ff:ff:ff:ff"
    AGE_SECONDS = 300

    def __init__(self, ports):
        # Number of switch ports
        self.ports = ports

        # MAC table: {mac: (port, last_seen_time)}
        self.mac_table = {}

        # Current simulation time
        self.current_time = 0.0

    def handle(self, frame, in_port):
        """Learn from the source, then decide where the frame goes.

        Rules:
          1. Learn source MAC address.
          2. Never forward back to the incoming port.
          3. Broadcast -> every other port.
          4. Known destination -> destination port only.
          5. Unknown destination -> flooding.
        """

        # Unpack the incoming frame
        src_mac, dst_mac, time = frame
        self.current_time = time

        # --------------------------------------------------
        # Step 1: Aging
        # Remove MAC entries older than AGE_SECONDS.
        # --------------------------------------------------
        expired = [
            mac
            for mac, (_, last_seen) in self.mac_table.items()
            if time - last_seen > self.AGE_SECONDS
        ]

        for mac in expired:
            del self.mac_table[mac]

        # --------------------------------------------------
        # Step 2: Self-learning
        # Update source MAC address and incoming port.
        # This also handles stations moving between ports.
        # --------------------------------------------------
        self.mac_table[src_mac] = (in_port, time)

        # --------------------------------------------------
        # Step 3: Find all ports except the incoming port.
        # The range() order guarantees ascending output.
        # --------------------------------------------------
        other_ports = [
            port
            for port in range(self.ports)
            if port != in_port
        ]

        # --------------------------------------------------
        # Step 4: Broadcast destination
        # Forward to every other port.
        # --------------------------------------------------
        if dst_mac == self.BROADCAST:
            return other_ports

        # --------------------------------------------------
        # Step 5: Known destination
        # Forward only to the learned destination port.
        # --------------------------------------------------
        if dst_mac in self.mac_table:
            out_port = self.mac_table[dst_mac][0]

            # Never send a frame back to its incoming port.
            if out_port == in_port:
                return []

            return [out_port]

        # --------------------------------------------------
        # Step 6: Unknown destination
        # Flood to every other port.
        # --------------------------------------------------
        return other_ports

    def table(self):
        """Return {mac: port} without aged-out entries.

        Expired entries are removed during handle().
        """

        return {
            mac: port
            for mac, (port, _) in self.mac_table.items()
        }


# ------------------------------------------------------------------- harness
A, B, C = "00:00:00:00:00:0a", "00:00:00:00:00:0b", "00:00:00:00:00:0c"
BC = Switch.BROADCAST


def verify():
    fails = 0

    def check(label, got, want):
        nonlocal fails
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<46} {got}"
              + ("" if ok else f"   want {want}"))
        fails += not ok

    try:
        s = Switch(4)
    except NotImplementedError:
        print("  Switch is still a stub")
        return 1

    # A talks to B. Nobody knows B yet, so it floods
    # but not back to port 0.
    check("unknown destination floods",
          s.handle((A, B, 0.0), 0), [1, 2, 3])

    # Now B answers from port 2.
    # The switch has seen A, so it forwards precisely.
    check("known destination is not flooded",
          s.handle((B, A, 1.0), 2), [0])

    check("learned both",
          s.table(), {A: 0, B: 2})

    # Broadcast always goes everywhere except back.
    check("broadcast floods",
          s.handle((A, BC, 2.0), 0), [1, 2, 3])

    # A frame for yourself must not come back
    # out of the port it came in on.
    check("never back out the arrival port",
          s.handle((C, A, 3.0), 0), [])

    # B moves to port 3.
    # The switch must believe the new evidence.
    check("station moved, table follows",
          (s.handle((B, A, 4.0), 3), s.table()[B]), ([0], 3))

    # Nothing heard from A for longer than AGE_SECONDS.
    # It must be forgotten.
    s.handle((C, BC, 400.0), 1)

    check("aged-out entry is gone",
          A in s.table(), False)

    print(f"\n  {'all ok' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
