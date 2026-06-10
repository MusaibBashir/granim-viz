"""Iterative reversal — prev/cur/nxt badges hop node to node; each arrow flip
is classified from the recently removed reverse edge."""
import granim as ga


@ga.animate(debug=True, show=False)
def reverse_iterative(head):
    prev, cur = None, head
    while cur is not None:
        nxt = cur.next
        cur.next = prev
        prev, cur = cur, nxt
    return prev


if __name__ == "__main__":
    head = reverse_iterative(ga.linked_list([1, 2, 3, 4, 5]).head)
    print("new head:", head)
