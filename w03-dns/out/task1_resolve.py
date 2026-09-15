#!/usr/bin/env python3
"""Educational iterative DNS resolver: root -> TLD -> authoritative server."""

from __future__ import annotations

import argparse
import ipaddress
import subprocess
from typing import Iterable

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rdatatype


# Start with literal root-server addresses so the first query needs no resolver.
ROOT_SERVERS = [
    "198.41.0.4", "170.247.170.2", "192.33.4.12", "199.7.91.13",
    "192.203.230.10", "192.5.5.241", "192.112.36.4", "198.97.190.53",
    "192.36.148.17", "192.58.128.30", "193.0.14.129", "199.7.83.42",
    "202.12.27.33",
]


class ResolutionError(RuntimeError):
    pass


class Resolver:
    def __init__(self, timeout: float = 2.0, max_depth: int = 30,
                 max_cnames: int = 12) -> None:
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_cnames = max_cnames

    def _ask(self, server: str, name: str):
        """Send a non-recursive A query to one candidate nameserver."""
        query = dns.message.make_query(name, dns.rdatatype.A, use_edns=True)
        query.flags &= ~dns.flags.RD       # equivalent to dig +norecurse
        return dns.query.udp(query, server, timeout=self.timeout)

    @staticmethod
    def _a_records(message, owner: dns.name.Name) -> list[str]:
        return [record.address for rrset in message.answer
                if rrset.rdtype == dns.rdatatype.A and rrset.name == owner
                for record in rrset]

    @staticmethod
    def _cname_target(message, owner: dns.name.Name) -> str | None:
        for rrset in message.answer:
            if rrset.rdtype == dns.rdatatype.CNAME and rrset.name == owner:
                return str(next(iter(rrset)).target)
        return None

    @staticmethod
    def _referral_ns(message) -> list[str]:
        return [str(record.target) for rrset in message.authority
                if rrset.rdtype == dns.rdatatype.NS for record in rrset]

    @staticmethod
    def _glue(message, ns_names: Iterable[str]) -> list[str]:
        wanted = {dns.name.from_text(name) for name in ns_names}
        return [record.address for rrset in message.additional
                if rrset.rdtype == dns.rdatatype.A and rrset.name in wanted
                for record in rrset]

    def resolve(self, name: str) -> tuple[str, list[str]]:
        """Return (one IPv4 address, ordered list of queried DNS servers)."""
        return self._resolve(dns.name.from_text(name).to_text(), 0, 0, set())

    def _resolve(self, name: str, depth: int, cname_count: int,
                 seen: set[str]) -> tuple[str, list[str]]:
        if depth >= self.max_depth:
            raise ResolutionError("maximum DNS delegation depth reached")
        if name in seen:
            raise ResolutionError(f"DNS loop detected at {name}")

        seen = seen | {name}
        candidates = list(ROOT_SERVERS)
        path: list[str] = []
        owner = dns.name.from_text(name)

        while candidates:
            if depth >= self.max_depth:
                raise ResolutionError("maximum DNS delegation depth reached")
            depth += 1
            next_candidates: list[str] = []

            # If a server times out or fails, continue with the next NS server.
            for server in candidates:
                try:
                    ipaddress.ip_address(server)
                    response = self._ask(server, name)
                    path.append(server)
                except (ValueError, OSError, dns.exception.DNSException):
                    continue

                addresses = self._a_records(response, owner)
                if addresses:
                    return addresses[0], path

                target = self._cname_target(response, owner)
                if target:
                    if cname_count >= self.max_cnames:
                        raise ResolutionError("maximum CNAME depth reached")
                    address, cname_path = self._resolve(
                        target, depth, cname_count + 1, seen
                    )
                    return address, path + cname_path

                ns_names = self._referral_ns(response)
                if not ns_names:
                    continue

                glue = self._glue(response, ns_names)
                if glue:
                    next_candidates.extend(glue)
                else:
                    # No glue: recursively perform a separate root walk for
                    # each NS hostname, then use the discovered address(es).
                    for ns_name in ns_names:
                        try:
                            ns_ip, ns_path = self._resolve(ns_name, depth, 0, seen)
                            path.extend(ns_path)
                            next_candidates.append(ns_ip)
                        except ResolutionError:
                            continue
                if next_candidates:
                    break

            candidates = list(dict.fromkeys(next_candidates))

        raise ResolutionError(f"could not resolve {name} iteratively")


def main() -> int:
    parser = argparse.ArgumentParser(description="Iterative, non-recursive DNS A lookup")
    parser.add_argument("name", nargs="?", default="www.korea.ac.kr")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    names = (["www.korea.ac.kr", "www.example.com", "www.iana.org",
              "www.wikipedia.org", "www.cloudflare.com"] if args.verify else [args.name])

    resolver = Resolver()
    failed = False
    for name in names:
        try:
            address, path = resolver.resolve(name)
            if args.verify:
                # dig is used only as an independent check, never to perform
                # the iterative walk above.
                completed = subprocess.run(
                    ["dig", "+short", name, "A"], text=True,
                    capture_output=True, check=False
                )
                dig_addresses = [line.strip() for line in completed.stdout.splitlines()
                                 if line.strip() and _is_ipv4(line.strip())]
                if not dig_addresses:
                    raise ResolutionError("dig verification returned no A record")
                status = "ok" if address in dig_addresses else "note"
                print(f"{status:<5} {name:<25} you={address:<15} "
                      f"dig={dig_addresses[0]:<15} hops={len(path)}")
                if status == "note":
                    print("      different CDN/load-balanced answer; record this in observation.md")
            else:
                print(f"ok    {name:<25} you={address:<15} hops={len(path)}")
            print("      " + " -> ".join(path))
        except (OSError, ResolutionError) as exc:
            failed = True
            print(f"fail  {name}: {exc}")
    return int(failed)


def _is_ipv4(value: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(value), ipaddress.IPv4Address)
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
