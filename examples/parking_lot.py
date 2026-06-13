"""Parking Lot counting - visualize the end and middle cases.

For a concrete n=5, the row has 2n-2 = 8 spaces. The animation highlights the
block of exactly n equal cars, the adjacent cars that must be different, and
the remaining free choices that create the formula.
"""
import granim as ga


def _reset(row, n):
    for i in range(2 * n - 2):
        row[i] = "."
        row[i].state = "default"


def _paint_case(row, n, start):
    length = 2 * n - 2
    _reset(row, n)
    blocked = set(range(start, start + n))
    guards = {i for i in (start - 1, start + n) if 0 <= i < length}
    for i in range(length):
        if i in blocked:
            row[i] = "A"
            row[i].state = "active"
        elif i in guards:
            row[i] = "!=A"
            row[i].state = "frontier"
        else:
            row[i] = "*"
            row[i].state = "visited"


def visualize(n=5):
    length = 2 * n - 2
    end_each = 4 * 3 * (4 ** (n - 3))
    end_total = 2 * end_each
    middle_each = 4 * (3 ** 2) * (4 ** (n - 4))
    middle_total = (n - 3) * middle_each
    total = end_total + middle_total

    with ga.record(debug=True, title="Parking Lot counting", speed=0.75) as rec:
        row = ga.array(["."] * length)
        count = ga.matrix([
            ["case", "positions", "ways per position", "subtotal"],
            ["end", "2", "4*3*4^(n-3)", str(end_total)],
            ["middle", "n-3", "4*3^2*4^(n-4)", str(middle_total)],
            ["total", "", "", str(total)],
        ])

        rec.watch(n=n, slots=length)
        rec.step(f"n={n}: parking lot length is 2n-2={length}")

        with rec.batch():
            _paint_case(row, n, 0)
            count[1][1].state = "active"
            count[1][2].state = "active"
            count[1][3].state = "frontier"
        rec.step("End case: first n slots are A; right neighbor has 3 choices")

        with rec.batch():
            _paint_case(row, n, n - 2)
            count[1][1].state = "done"
            count[1][2].state = "done"
            count[1][3].state = "done"
        rec.step("There are 2 end positions, so end subtotal is 2*4*3*4^(n-3)")

        for start in range(1, n - 2):
            with rec.batch():
                _paint_case(row, n, start)
                count[2][1].state = "active"
                count[2][2].state = "active"
                count[2][3].state = "frontier"
            rec.step(
                f"Middle start {start + 1}: both neighbors must avoid A, so 3*3 choices"
            )

        with rec.batch():
            count[2][1].state = "done"
            count[2][2].state = "done"
            count[2][3].state = "done"
            count[3][3].state = "done"
        rec.step(
            "Total = 2*4*3*4^(n-3) + (n-3)*4*3^2*4^(n-4)"
        )

    rec.save(__file__.replace(".py", ".html"))
    return total


if __name__ == "__main__":
    print("ways for n=5 =", visualize(5))
