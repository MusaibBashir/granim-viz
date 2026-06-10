"""Binary search — one decorator, zero annotations. lo/hi/mid badges appear
automatically from the locals diff; comparisons pulse the cells."""
import granim as ga


@ga.animate(debug=True, show=False)
def binary_search(a, x):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == x:
            return mid
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


if __name__ == "__main__":
    arr = ga.array([2, 5, 8, 12, 16, 23, 38, 56, 72, 91])
    print("found at", binary_search(arr, 23))
