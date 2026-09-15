#!/usr/bin/env python3
"""Week 3 · Task 1 — Build your own iterative resolver."""

import argparse
import ipaddress
import subprocess
import sys

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rdatatype


# Root servers. Everything starts here; there is no earlier step.
ROOT_SERVERS = [
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
]

# Stable names should normally match dig exactly.
# Microsoft may return a CDN-dependent address.
VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class ResolutionError(RuntimeError):
    """The iterative DNS walk could not obtain an A record."""


class Resolver:
    """An iterative, non-recursive DNS A-record resolver."""

    def __init__(self, timeout=2.0, max_depth=30, max_cnames=12):
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_cnames = max_cnames

    def _ask(self, server, name):
        """Ask exactly one server without allowing recursion."""
        query = dns.message.make_query(name, dns.rdatatype.A, use_edns=True)
        query.flags &= ~dns.flags.RD  # Equivalent to dig +norecurse.
        return dns.query.udp(query, server, timeout=self.timeout)

    @staticmethod
    def _a_records(response, owner):
        """Return A records whose owner is exactly the requested name."""
        addresses = []

        for rrset in response.answer:
            if rrset.rdtype == dns.rdatatype.A and rrset.name == owner:
                addresses.extend(record.address for record in rrset)

        return addresses

    @staticmethod
    def _cname_target(response, owner):
        """Return the CNAME target for owner, if one was returned."""
        for rrset in response.answer:
            if rrset.rdtype == dns.rdatatype.CNAME and rrset.name == owner:
                return str(next(iter(rrset)).target)

        return None

    @staticmethod
    def _delegated_nameservers(response):
        """Extract NS hostnames from the Authority section of a referral."""
        nameservers = []

        for rrset in response.authority:
            if rrset.rdtype == dns.rdatatype.NS:
                nameservers.extend(str(record.target) for record in rrset)

        return nameservers

    @staticmethod
    def _glue_addresses(response, nameservers):
        """Extract glue A records for the delegated nameservers."""
        ns_names = {dns.name.from_text(server) for server in nameservers}
        addresses = []

        for rrset in response.additional:
            if rrset.rdtype == dns.rdatatype.A and rrset.name in ns_names:
                addresses.extend(record.address for record in rrset)

        return addresses

    def resolve(self, name):
        """
        Resolve name iteratively.

        Returns:
            (address, path)

        address is the final A-record string.
        path is the ordered list of DNS server IPs queried.
        """
        normalized_name = dns.name.from_text(name).to_text()

        return self._resolve(
            normalized_name,
            depth=0,
            cname_count=0,
            seen_names=set(),
        )

    def _resolve(self, name, depth, cname_count, seen_names):
        """Perform one complete root-to-authoritative walk."""
        if depth >= self.max_depth:
            raise ResolutionError("maximum delegation depth reached")

        if name in seen_names:
            raise ResolutionError(f"DNS loop detected at {name}")

        seen_names = seen_names | {name}
        owner = dns.name.from_text(name)
        candidates = list(ROOT_SERVERS)
        path = []

        while candidates:
            if depth >= self.max_depth:
                raise ResolutionError("maximum delegation depth reached")

            depth += 1
            next_candidates = []

            # Try every available server. A timeout must not end the walk.
            for server in candidates:
                try:
                    ipaddress.ip_address(server)
                    response = self._ask(server, name)
                    path.append(server)
                except (
                    ValueError,
                    OSError,
                    dns.exception.DNSException,
                ):
                    continue

                # An authoritative answer contains the requested A record.
                addresses = self._a_records(response, owner)
                if addresses:
                    return addresses[0], path

                # A CNAME requires a fresh root walk for its target.
                target = self._cname_target(response, owner)
                if target is not None:
                    if cname_count >= self.max_cnames:
                        raise ResolutionError("maximum CNAME depth reached")

                    address, cname_path = self._resolve(
                        target,
                        depth=depth,
                        cname_count=cname_count + 1,
                        seen_names=seen_names,
                    )
                    return address, path + cname_path

                # A referral supplies NS names in Authority.
                nameservers = self._delegated_nameservers(response)
                if not nameservers:
                    continue

                glue = self._glue_addresses(response, nameservers)

                if glue:
                    next_candidates.extend(glue)
                else:
                    # No glue: first resolve each NS hostname through another
                    # iterative root walk, then ask its discovered IP address.
                    for ns_name in nameservers:
                        try:
                            ns_address, ns_path = self._resolve(
                                ns_name,
                                depth=depth,
                                cname_count=0,
                                seen_names=seen_names,
                            )
                            path.extend(ns_path)
                            next_candidates.append(ns_address)
                        except ResolutionError:
                            continue

                if next_candidates:
                    break

            # Remove duplicates while preserving nameserver order.
            candidates = list(dict.fromkeys(next_candidates))

        raise ResolutionError(f"could not resolve {name} iteratively")


# ------------------------------------------------------------------- harness

def dig_answer(name):
    """Obtain A records from dig only for verification."""
    try:
        result = subprocess.run(
            ["dig", "+short", name, "A"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError("dig is required for --verify") from exc

    answers = []

    for line in result.stdout.splitlines():
        value = line.strip()

        try:
            ipaddress.IPv4Address(value)
            answers.append(value)
        except ipaddress.AddressValueError:
            pass

    return answers


def verify():
    resolver = Resolver()
    failures = 0

    for name, kind in VERIFY_NAMES:
        try:
            address, path = resolver.resolve(name)
            expected = dig_answer(name)
        except Exception as exc:
            print(f"  FAIL  {name:<22} your resolver raised {exc!r}")
            failures += 1
            continue

        if address in expected:
            status = "ok"
            note = ""
        elif kind == "cdn":
            status = "ok"
            note = "  <- CDN/load-balanced answer differed; document this."
        else:
            status = "FAIL"
            note = "  <- should have matched"
            failures += 1

        print(
            f"  {status:<5} {name:<22} "
            f"you={address:<16} "
            f"dig={','.join(expected) or '-':<16} "
            f"hops={len(path)}{note}"
        )

    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", default="www.korea.ac.kr")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        sys.exit(verify())

    address, path = Resolver().resolve(args.name)

    for index, server in enumerate(path, 1):
        print(f"  {index}. asked {server}")

    print(f"\n  {args.name} -> {address}")


if __name__ == "__main__":
    main()
