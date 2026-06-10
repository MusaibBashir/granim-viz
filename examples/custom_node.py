"""Your own class, animated — no granim inheritance. @ga.node instruments it:
node-valued fields become labeled edges, the value field animates, the rest is
plain storage. LeetCode 138 with the exact class LeetCode gives you."""
import granim as ga


@ga.node(value="val", shape="pill")
class Node:
    def __init__(self, val):
        self.val = val
        self.next = None
        self.random = None


@ga.animate(debug=True, show=False)
def copy_random_list(head):
    # interleave copies: A -> A' -> B -> B' ...
    cur = head
    while cur is not None:
        dup = Node(cur.val)
        dup.next = cur.next
        cur.next = dup
        cur = dup.next
    cur = head
    while cur is not None:           # wire the copies' randoms
        if cur.random is not None:
            cur.next.random = cur.random.next
        cur = cur.next.next
    cur, new_head = head, head.next
    while cur is not None:           # unweave
        dup = cur.next
        cur.next = dup.next
        dup.next = dup.next.next if dup.next is not None else None
        cur = cur.next
    return new_head


if __name__ == "__main__":
    a, b, c = Node(7), Node(13), Node(11)
    a.next, b.next = b, c
    a.random, c.random = c, a
    head = copy_random_list(a)
    out = []
    while head is not None:
        out.append(head.val)
        head = head.next
    print(out)
