from typing import Optional
import granim as ga


@ga.node(value="val", shape="circle")
class Node:
    def __init__(self, val: int):
        self.val = val
        self.next = None
        self.random = None
class Solution:
    @ga.animate(debug=True, show=True, title="Copy List with Random Pointer")
    def copyRandomList(self, head: Optional[Node]) -> Optional[Node]:
        if head is None:
            return None

        cur = head
        while cur is not None:
            copy = Node(cur.val)
            copy.next = cur.next
            cur.next = copy
            cur = copy.next

        cur = head
        while cur is not None:
            copy = cur.next
            if cur.random is not None:
                copy.random = cur.random.next
            cur = copy.next

        cur = head
        new_head = head.next
        while cur is not None:
            copy = cur.next
            cur.next = copy.next
            if copy.next is not None:
                copy.next = copy.next.next
            cur = cur.next

        return new_head
a = Node(7)
b = Node(13)
c = Node(11)
d = Node(10)
e = Node(1)

a.next = b
b.next = c
c.next = d
d.next = e

b.random = a
c.random = e
d.random = c
e.random = a

copied = Solution().copyRandomList(a)