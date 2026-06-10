"""Flood fill on a matrix — values change as the region fills, colors spread
cell by cell, and the call stack shows the recursion."""
import granim as ga

m = ga.matrix([
    [1, 1, 0, 0, 2],
    [1, 0, 0, 2, 2],
    [1, 1, 1, 0, 2],
    [0, 1, 0, 0, 0],
    [1, 1, 0, 2, 2],
])


@ga.animate(debug=True, show=False)
def flood_fill(m, i, j, old, new):
    if not (0 <= i < len(m) and 0 <= j < m.cols):
        return
    if m[i][j] != old:
        return
    m[i][j] = new
    m[i][j].state = "visited"
    flood_fill(m, i + 1, j, old, new)
    flood_fill(m, i - 1, j, old, new)
    flood_fill(m, i, j + 1, old, new)
    flood_fill(m, i, j - 1, old, new)


if __name__ == "__main__":
    flood_fill(m, 0, 0, 1, 7)
    print(m.to_lists())
