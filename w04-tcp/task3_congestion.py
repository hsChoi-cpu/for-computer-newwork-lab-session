#!/usr/bin/env python3
"""Week 4 · Task 3 — congestion control for the simulated link."""


class FixedWindow:
    """Send 64 packets at a time and never listen."""

    def __init__(self):
        self.window = 64

    def on_ack(self):
        pass

    def on_loss(self):
        pass


class YourControl:
    """Probe for the first drop, then keep a safety margin below that window."""

    def __init__(self):
        self.window = 1.0
        self.ceiling = None

    def on_ack(self):
        if self.ceiling is None and self.window < 16:
            self.window += 1.0
        else:
            self.window = min(self.ceiling or float("inf"),
                              self.window + 1.0 / self.window)

    def on_loss(self):
        if self.ceiling is None:
            # A timeout arrives well after the queue overflow. Leave room for
            # packets already in flight when the first drop was detected.
            self.ceiling = max(2, int(self.window * 0.75))
        self.window = min(self.window, self.ceiling)
