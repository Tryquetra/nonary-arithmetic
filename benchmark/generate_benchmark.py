#!/usr/bin/env python3
"""Benchmark for the nonary/octal bridge conversions of the paper.

Reproduces the measured results of Section 8 of index.html:
counts of passes and digit-steps for the direct and bridge routes on
random inputs with n = 1000 source digits. Deterministic when given the
same seed. Requires only the Python standard library.
"""

import random
import sys

N = 1000            # number of source digits
TRIALS = 40         # inputs averaged per route (stabilizes the counts)
SEED = 20261025


def random_digits(n, base, rng):
    """n random base-`base` digits from `rng`, most significant first, nonzero leading digit."""
    return [rng.randrange(1, base)] + [rng.randrange(base) for _ in range(n - 1)]


def value(digits, base):
    v = 0
    for d in digits:
        v = v * base + d
    return v


def adjacent_pass(a, p, q):
    """One pass of the p -> p±1 algorithm (Section 2).

    Divides base-p digits `a` by q = p-1 or p+1. Returns the quotient
    digits (trimmed), the remainder, and the number of digit-steps used.
    """
    sigma = q - p
    c = 0
    quotient = []
    for d in a:
        v = d - sigma * c
        quotient.append(c + v // q)
        c = v % q
    i = 0
    while i < len(quotient) - 1 and quotient[i] == 0:
        i += 1
    return quotient[i:], c, len(a)


def convert_adjacent(digits, p, q):
    """Repeated-pass conversion p -> q via the adjacent-base algorithm.

    Returns (output digits in base q, passes, digit-steps).
    """
    out = []
    passes = 0
    steps = 0
    cur = digits
    while cur and not (len(cur) == 1 and cur[0] == 0):
        cur, r, s = adjacent_pass(cur, p, q)
        passes += 1
        steps += s
        out.append(r)
    return out[::-1] or [0], passes, steps


def convert_direct(digits, p, q):
    """Generic short-division conversion p -> q (baseline).

    Each pass divides the current base-p digits by q with a running
    remainder; a step is one digit processed inside a pass.
    """
    out = []
    passes = 0
    steps = 0
    cur = digits
    while cur and not (len(cur) == 1 and cur[0] == 0):
        rem = 0
        nxt = []
        steps += len(cur)
        for d in cur:
            v = rem * p + d
            nxt.append(v // q)
            rem = v % q
        i = 0
        while i < len(nxt) - 1 and nxt[i] == 0:
            i += 1
        cur = nxt[i:]
        out.append(rem)
        passes += 1
    return out[::-1] or [0], passes, steps


def group(digits, k, base):
    """Group source-base digits from the right into k-digit chunks (pad leading zeros)."""
    if len(digits) % k:
        digits = [0] * (k - len(digits) % k) + digits
    return [sum(digits[i + j] * base ** (k - 1 - j) for j in range(k))
            for i in range(0, len(digits), k)]


def split(digits, k, base):
    """Expand base-`base` digits into k digits each in base base (inverse of group)."""
    out = []
    for d in digits:
        for j in range(k - 1, -1, -1):
            out.append((d // (base ** j)) % base)
    i = 0
    while i < len(out) - 1 and out[i] == 0:
        i += 1
    return out[i:]


def check_consistency():
    """Verify adjacent routes equal direct routes on random inputs."""
    rng = random.Random(SEED)
    for p in range(2, 37):
        for q in (p - 1, p + 1):
            if not 2 <= q <= 36:
                continue
            for _ in range(20):
                d = random_digits(rng.randrange(1, 201), p, rng)
                assert convert_adjacent(d, p, q)[0] == convert_direct(d, p, q)[0]
                assert value(convert_adjacent(d, p, q)[0], q) == value(d, p)
                assert value(convert_direct(d, p, q)[0], q) == value(d, p)
    # Fixed examples from the paper.
    assert convert_adjacent([1, 2, 3, 4], 10, 9)[0] == [1, 6, 2, 1]
    assert convert_adjacent([1, 6, 2, 1], 9, 10)[0] == [1, 2, 3, 4]
    # Section 6/7 examples: 1200201_3 -> 10011010010_2 via nonary and octal.
    assert split(convert_adjacent(group([1, 2, 0, 0, 2, 0, 1], 2, 3), 9, 8)[0], 3, 2) == [1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0]


def check_bridge_routes():
    """Verify every bridge route reproduces the source value."""
    rng = random.Random(SEED)
    for _ in range(5):
        dec = random_digits(rng.randrange(100, 400), 10, rng)
        tri = random_digits(rng.randrange(100, 400), 3, rng)
        bit = random_digits(rng.randrange(100, 400), 2, rng)

        # 10 -> 3 via nonary.
        nonary = convert_adjacent(dec, 10, 9)[0]
        assert value(split(nonary, 2, 3), 3) == value(dec, 10)

        # 3 -> 2 via nonary and octal.
        octal = convert_adjacent(group(tri, 2, 3), 9, 8)[0]
        assert value(split(octal, 3, 2), 2) == value(tri, 3)

        # 3 -> 2 via quaternary.
        quat = convert_adjacent(tri, 3, 4)[0]
        assert value(split(quat, 2, 2), 2) == value(tri, 3)

        # 2 -> 3 via octal and nonary.
        nonary2 = convert_adjacent(group(bit, 3, 2), 8, 9)[0]
        assert value(split(nonary2, 2, 3), 3) == value(bit, 2)

        # 3 -> 10 via nonary.
        dec2 = convert_adjacent(group(tri, 2, 3), 9, 10)[0]
        assert value(dec2, 10) == value(tri, 3)


def route_stats(make_input, route):
    """Average pass/step counts over TRIALS random inputs."""
    rng = random.Random(SEED)
    tp = ts = 0
    for _ in range(TRIALS):
        digits = make_input(rng)
        _, p, s = route(digits)
        tp += p
        ts += s
    return round(tp / TRIALS), round(ts / TRIALS)


def main():
    check_consistency()
    check_bridge_routes()

    def dec(rng):
        return random_digits(N, 10, rng)

    def trits(rng):
        return random_digits(N, 3, rng)

    def bits(rng):
        return random_digits(N, 2, rng)

    # role: "required" when source and target are not adjacent, so the bridge
    # is the only way to use the adjacent-base algorithm; "optional" when the
    # direct adjacent conversion already exists and the bridge only reduces
    # digit-steps. "baseline" names what the direct column measures.
    rows = [
        ("required", "$10 \\to 3$", "short division", "9", dec,
         lambda d: convert_direct(d, 10, 3),
         lambda d: convert_adjacent(d, 10, 9), 2),
        ("required", "$3 \\to 10$", "short division", "9", trits,
         lambda d: convert_direct(d, 3, 10),
         lambda d: convert_adjacent(group(d, 2, 3), 9, 10), 1),
        ("optional", "$3 \\to 2$", "adjacent", "9 and 8", trits,
         lambda d: convert_direct(d, 3, 2),
         lambda d: convert_adjacent(group(d, 2, 3), 9, 8), 3),
        ("optional", "$3 \\to 2$", "adjacent", "4", trits,
         lambda d: convert_direct(d, 3, 2),
         lambda d: convert_adjacent(d, 3, 4), 2),
        ("optional", "$2 \\to 3$", "adjacent", "8 and 9", bits,
         lambda d: convert_direct(d, 2, 3),
         lambda d: convert_adjacent(group(d, 3, 2), 8, 9), 2),
    ]

    header = ("| Route | Bridge | Passes direct | Passes bridge | Pass ratio "
              "| Steps direct | Steps bridge | Step ratio | Width-weighted gain |")
    rule = "|---|---|---|---|---|---|---|---|---|"

    for role, label in (("required", "bridge required (source and target not adjacent)"),
                        ("optional", "bridge optional (source and target already adjacent)")):
        print(f"\n{label}\n")
        print(header)
        print(rule)
        for r_role, name, baseline, bridge, make, direct, bridge_route, wgain in rows:
            if r_role != role:
                continue
            pd, sd = route_stats(make, direct)
            pb, sb = route_stats(make, bridge_route)
            print(f"| {name} | {bridge} | {pd} | {pb} | {pd / pb:.2f} "
                  f"| {sd:,} | {sb:,} | {sd / sb:.2f} | {wgain} |")

    # Model prediction used in Section 8.
    l = N * 2.302585092994046 / 1.0986122886681098
    print(f"\nmodel: n*L/2 = {N}*{l:.0f}/2 = {N * l / 2:,.0f} digit-steps (direct 10 -> 3)")

    # Scaling check quoted in Section 8.
    for n in (100, 3000):
        rng = random.Random(SEED)
        tp = ts = 0
        for _ in range(10):
            d = random_digits(n, 10, rng)
            _, p, s = convert_direct(d, 10, 3)
            tp += p
            ts += s
        pd, sd = tp / 10, ts / 10
        tp = ts = 0
        for _ in range(10):
            d = random_digits(n, 10, rng)
            _, p, s = convert_adjacent(d, 10, 9)
            tp += p
            ts += s
        pb, sb = tp / 10, ts / 10
        print(f"scaling n={n}: 10->3 pass ratio {pd / pb:.2f}, step ratio {sd / sb:.2f}")


if __name__ == "__main__":
    sys.exit(main())
