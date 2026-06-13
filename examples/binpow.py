"""Binary exponentiation - watch the low bit choose whether `res` multiplies.

The scalar variables from the usual loop are mirrored into a small matrix so
their updates are visible, and the exponent bits are shown least-significant
bit first because `b >>= 1` consumes them from right to left.
"""
import granim as ga


@ga.animate(debug=True, show=False, title="Binary exponentiation")
def binpow(a, b, m):
    original_b = b
    a %= m
    res = 1

    values = ga.matrix([
        ["a", a],
        ["b", b],
        ["res", res],
        ["m", m],
    ])
    bits = ga.array([int(bit) for bit in reversed(bin(original_b)[2:])])

    bit_i = 0
    while b > 0:
        bits[bit_i].state = "active"
        if bits[bit_i] == 1:          # same branch as `if (b & 1)`
            res = res * a % m
            values[2][1] = res
            values[2][1].state = "frontier"
        else:
            values[2][1].state = "visited"

        a = a * a % m
        values[0][1] = a
        values[0][1].state = "visited"

        b >>= 1
        values[1][1] = b
        bits[bit_i].state = "done"
        bit_i += 1

    values[2][1].state = "done"
    return res


if __name__ == "__main__":
    print("3^13 mod 17 =", binpow(3, 13, 17))
