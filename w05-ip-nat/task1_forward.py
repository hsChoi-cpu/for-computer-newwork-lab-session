#!/usr/bin/env python3
"""Week 5 · Task 1 — Subnets and longest-prefix match.

Textbook §4.3.2 (IPv4 addressing, CIDR) and §4.3.3 (forwarding).

Two things a router does with every packet: work out which prefixes the
destination falls inside, and pick the longest one. The second is the whole
of "longest prefix match", and it is the reason the internet's routing table
can hold a million entries and still be answerable.

You build both, from integers up. No `ipaddress` module - that library is
exactly the thing you are supposed to understand this week.

    python3 task1_forward.py --verify
"""
import argparse


# --------------------------------------------------------------- helpers
def ip_to_int(address):
    """Convert dotted-decimal IPv4 address to a 32-bit integer."""
    parts = address.split(".")

    if len(parts) != 4:
        raise ValueError(f"invalid IPv4 address: {address}")

    value = 0

    for part in parts:
        if not part or not part.isdigit():
            raise ValueError(f"invalid IPv4 address: {address}")

        octet = int(part)

        if octet < 0 or octet > 255:
            raise ValueError(f"invalid IPv4 address: {address}")

        value = (value << 8) | octet

    return value


def int_to_ip(value):
    """Convert a 32-bit integer to dotted-decimal IPv4."""
    if value < 0 or value > 0xFFFFFFFF:
        raise ValueError("IPv4 integer must fit in 32 bits")

    return ".".join([
        str((value >> 24) & 0xFF),
        str((value >> 16) & 0xFF),
        str((value >> 8) & 0xFF),
        str(value & 0xFF),
    ])


def prefix_mask(prefix):
    """Return the 32-bit mask for a prefix length."""
    if prefix < 0 or prefix > 32:
        raise ValueError("prefix length must be between 0 and 32")

    if prefix == 0:
        return 0

    return (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF


# --------------------------------------------------------------- Task 1
def parse_cidr(cidr):
    """'163.152.6.0/24' -> (network as int, prefix length).

    Requirements: reject a prefix length outside 0-32, and reject an address
    whose host bits are set when they should not be (163.152.6.5/24 is a
    common way to write a host, but it is not a network).
    """
    if cidr.count("/") != 1:
        raise ValueError(f"invalid CIDR: {cidr}")

    address_text, prefix_text = cidr.split("/")

    try:
        prefix = int(prefix_text)
    except ValueError:
        raise ValueError(f"invalid prefix length: {prefix_text}")

    if prefix < 0 or prefix > 32:
        raise ValueError("prefix length must be between 0 and 32")

    address = ip_to_int(address_text)
    mask = prefix_mask(prefix)

    network = address & mask

    # A CIDR network address may not contain host bits.
    if address != network:
        raise ValueError(f"host bits are set in network address: {cidr}")

    return network, prefix


def network_range(cidr):
    """'163.152.6.0/24' -> (first usable, last usable, broadcast) as strings.

    /31:
        Both addresses are considered usable, following RFC 3021's
        point-to-point interpretation.

    /32:
        The single address is treated as the only usable address.
    """
    network, prefix = parse_cidr(cidr)

    mask = prefix_mask(prefix)

    # Host bits become 1 to obtain the broadcast address.
    host_mask = (~mask) & 0xFFFFFFFF
    broadcast = network | host_mask

    if prefix == 32:
        first = network
        last = network

    elif prefix == 31:
        first = network
        last = broadcast

    else:
        first = network + 1
        last = broadcast - 1

    return (
        int_to_ip(first),
        int_to_ip(last),
        int_to_ip(broadcast),
    )


class ForwardingTable:
    """Longest-prefix-match forwarding.

    add(cidr, next_hop)  ·  lookup(address) -> next_hop or None

    The default route 0.0.0.0/0 matches everything and is the shortest prefix,
    so it must lose to any other match.

    If two matching entries have the same prefix length, the entry added
    first is kept.
    """

    def __init__(self):
        self.routes = []

    def add(self, cidr, next_hop):
        network, prefix = parse_cidr(cidr)

        self.routes.append(
            (network, prefix, next_hop)
        )

    def lookup(self, address):
        destination = ip_to_int(address)

        best_prefix = -1
        best_next_hop = None

        for network, prefix, next_hop in self.routes:
            mask = prefix_mask(prefix)

            # Destination belongs to this network.
            if (destination & mask) == network:
                # Strictly greater means a tie keeps the earlier entry.
                if prefix > best_prefix:
                    best_prefix = prefix
                    best_next_hop = next_hop

        return best_next_hop


# ------------------------------------------------------------------- harness
RANGE_CASES = [
    ("192.168.0.0/24",  "192.168.0.1",   "192.168.0.254",  "192.168.0.255"),
    ("10.0.0.0/8",      "10.0.0.1",      "10.255.255.254", "10.255.255.255"),
    ("172.16.32.0/20",  "172.16.32.1",   "172.16.47.254",  "172.16.47.255"),
    ("203.0.113.64/26", "203.0.113.65",  "203.0.113.126",  "203.0.113.127"),
]

TABLE = [
    ("0.0.0.0/0",       "default-gw"),
    ("10.0.0.0/8",      "campus"),
    ("10.20.0.0/16",    "eng-building"),
    ("10.20.30.0/24",   "lab-floor"),
    ("10.20.30.64/26",  "lab-rack-2"),
    ("192.168.1.0/24",  "home"),
]

LOOKUP_CASES = [
    ("10.20.30.70",   "lab-rack-2"),     # inside all four 10.x entries
    ("10.20.30.10",   "lab-floor"),
    ("10.20.99.1",    "eng-building"),
    ("10.99.0.1",     "campus"),
    ("8.8.8.8",       "default-gw"),
    ("192.168.1.77",  "home"),
]


def verify():
    fails = 0
    for cidr, first, last, bcast in RANGE_CASES:
        try:
            got = network_range(cidr)
        except NotImplementedError:
            print("  network_range is still a stub"); return 1
        except Exception as e:
            print(f"  FAIL  {cidr:<18} raised {e!r}"); fails += 1; continue
        ok = tuple(got) == (first, last, bcast)
        print(f"  {'ok  ' if ok else 'FAIL'}  {cidr:<18} {got}")
        fails += not ok

    t = ForwardingTable()
    try:
        for cidr, hop in TABLE:
            t.add(cidr, hop)
    except NotImplementedError:
        print("  ForwardingTable is still a stub"); return 1

    for addr, expect in LOOKUP_CASES:
        got = t.lookup(addr)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {addr:<16} -> {got}  (want {expect})")
        fails += not ok

    print(f"\n  {len(RANGE_CASES) + len(LOOKUP_CASES) - fails}"
          f"/{len(RANGE_CASES) + len(LOOKUP_CASES)} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
