#!/usr/bin/env python3
"""Week 4 · Task 1 — Build reliable delivery on top of an unreliable channel.

Textbook §3.4 (reliable data transfer) and §3.5 (TCP's sequence numbers).

    python3 task1_rdt.py --verify
"""
import argparse, hashlib, random

PAYLOAD = 8


class UnreliableChannel:
    """Loses 10%, duplicates 3%, reorders, and delays. Deterministic by seed."""

    def __init__(self, seed=246, loss=0.10, dup=0.03, reorder=0.10):
        self.rng = random.Random(seed)
        self.loss, self.dup, self.reorder = loss, dup, reorder
        self.wire = []
        self.stats = {"sent": 0, "lost": 0, "duplicated": 0, "delivered": 0}

    def send(self, packet):
        self.stats["sent"] += 1
        if self.rng.random() < self.loss:
            self.stats["lost"] += 1
            return
        copies = 2 if self.rng.random() < self.dup else 1
        self.stats["duplicated"] += copies - 1
        for _ in range(copies):
            if self.rng.random() < self.reorder and self.wire:
                self.wire.insert(self.rng.randrange(len(self.wire)), packet)
            else:
                self.wire.append(packet)

    def receive(self):
        if not self.wire:
            return None
        self.stats["delivered"] += 1
        return self.wire.pop(0)


class Sender:
    """Stop-and-wait sender with numbered data and ACKs."""

    TIMEOUT = 4

    def __init__(self, data_channel, ack_channel, data):
        self.data_channel = data_channel
        self.ack_channel = ack_channel
        self.pieces = [data[i:i + PAYLOAD] for i in range(0, len(data), PAYLOAD)]
        self.next_seq = 0
        self.elapsed = self.TIMEOUT

    def step(self):
        if self.next_seq == len(self.pieces):
            return False

        ack = self.ack_channel.receive()
        if isinstance(ack, tuple) and len(ack) == 2 and ack == ("ACK", self.next_seq):
            self.next_seq += 1
            self.elapsed = self.TIMEOUT
            if self.next_seq == len(self.pieces):
                return False

        if self.elapsed >= self.TIMEOUT:
            self.data_channel.send(("DATA", self.next_seq, self.pieces[self.next_seq]))
            self.elapsed = 0
        else:
            self.elapsed += 1
        return True


class Receiver:
    """Accepts each numbered piece exactly once, in sequence."""

    def __init__(self, data_channel, ack_channel):
        self.data_channel = data_channel
        self.ack_channel = ack_channel
        self.expected = 0
        self.output = bytearray()

    def step(self):
        packet = self.data_channel.receive()
        if not isinstance(packet, tuple) or len(packet) != 3 or packet[0] != "DATA":
            return
        _, seq, payload = packet
        if seq == self.expected:
            self.output.extend(payload)
            self.expected += 1
        if seq < self.expected:
            self.ack_channel.send(("ACK", seq))

    def data(self):
        return bytes(self.output)


# ------------------------------------------------------------------- harness
def verify(seed=246, size=2000, max_steps=200_000):
    original = bytes(random.Random(seed).getrandbits(8) for _ in range(size))
    up, down = UnreliableChannel(seed), UnreliableChannel(seed + 1)

    sender = Sender(up, down, original)
    receiver = Receiver(up, down)

    for _ in range(max_steps):
        alive = sender.step()
        receiver.step()
        if not alive and len(receiver.data() or b"") >= size:
            break

    got = receiver.data() or b""
    ok = hashlib.sha256(got).hexdigest() == hashlib.sha256(original).hexdigest()
    print(f"  bytes    sent {size}   received {len(got)}")
    print(f"  channel  {up.stats}")
    print(f"  result   {'IDENTICAL' if ok else 'CORRUPTED OR INCOMPLETE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    p.add_argument("--seed", type=int, default=246)
    a = p.parse_args()
    raise SystemExit(verify(a.seed) if a.verify else p.print_help())
