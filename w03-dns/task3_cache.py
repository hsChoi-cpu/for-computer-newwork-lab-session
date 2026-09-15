#!/usr/bin/env python3
"""Week 3 · Task 3 — Beat the baseline cache.

Textbook §2.4.2 (caching) and §2.4.3 (TTL).
"""


class BaselineCache:
    """A DNS cache that somebody wrote in a hurry."""

    FIXED_LIFETIME = 60

    def __init__(self, upstream):
        self.upstream = upstream
        self.entries = []

    def lookup(self, name, now):
        """Return an address for `name`, asking upstream only if needed."""
        for entry in self.entries:
            if entry[0] == name:
                if now - entry[2] < self.FIXED_LIFETIME:
                    return entry[1]
                self.entries.remove(entry)
                break

        address, ttl = self.upstream(name)
        self.entries.append([name, address, now])
        return address

    def stats(self):
        return {"entries": len(self.entries)}


class YourCache:
    """A correct DNS cache that respects each authoritative TTL."""

    def __init__(self, upstream):
        self.upstream = upstream
        # name -> (address, expires_at)
        self.entries = {}

    def lookup(self, name, now):
        """Return a non-expired address, refreshing it only when necessary."""
        entry = self.entries.get(name)

        if entry is not None:
            address, expires_at = entry
            if now < expires_at:
                return address

            # Expired data must never be returned.
            del self.entries[name]

        address, ttl = self.upstream(name)

        # TTL is measured from the moment the authoritative response arrives.
        # A zero TTL is stored with immediate expiry, so the next lookup
        # correctly asks upstream again.
        expires_at = now + max(0, ttl)
        self.entries[name] = (address, expires_at)

        return address

    def stats(self):
        return {"entries": len(self.entries)}
