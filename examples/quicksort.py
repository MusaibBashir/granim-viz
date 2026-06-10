"""Quicksort — pivot glows, i/j badges sweep, swaps animate, sorted cells
turn done."""
import granim as ga


@ga.animate(debug=True, show=False)
def quicksort(a, lo=0, hi=None):
    if hi is None:
        hi = len(a) - 1
    if lo >= hi:
        if 0 <= lo == hi:
            a[lo].state = "done"
        return a
    pivot = a[hi]
    a[hi].state = "active"
    i = lo
    for j in range(lo, hi):
        if a[j] < pivot:
            a.swap(i, j)
            i += 1
    a.swap(i, hi)
    a[i].state = "done"
    quicksort(a, lo, i - 1)
    quicksort(a, i + 1, hi)
    return a


if __name__ == "__main__":
    print(quicksort(ga.array([6, 2, 8, 4, 9, 1, 5])).to_list())
